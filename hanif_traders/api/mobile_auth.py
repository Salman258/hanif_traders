import frappe
from frappe.utils import now_datetime
from hanif_traders.api.response import create_response, SUCCESS, UNAUTHORIZED, VALIDATION_ERROR

# Email reserved for the Google Play reviewer sandbox account.
# Requests from this email are auto-approved against a pre-seeded Technician
# whose data is fully synthetic. See hanif_traders/patches/seed_review_sandbox.py.
TEST_ACCOUNT_EMAIL = "google.reviewer@haniftraders.com"


def _auto_approve_if_test(request_doc, email):
	"""Auto-approves a Mobile Access Request when the email matches the
	Play Console reviewer sandbox account, so reviewers don't need a human
	to approve their device. Safe to call multiple times.

	Runs as Administrator because the approval chain calls
	frappe.core.doctype.user.user.generate_keys, which writes
	User.api_secret and requires User write permission — not available
	to the Guest session the mobile auth endpoint runs under.
	"""
	if email != TEST_ACCOUNT_EMAIL or request_doc.status == "Approved":
		return
	original_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		request_doc.status = "Approved"
		request_doc.save(ignore_permissions=True)
		frappe.db.commit()
	finally:
		frappe.set_user(original_user)


@frappe.whitelist(allow_guest=True)
def request_mobile_access(email, device_name=None, device_id=None):
	"""
	Creates a Mobile Access Request for the user with the given email.
	"""
	if not email or not device_id:
		frappe.throw("Invalid Request")

	# Find Employee by User ID, Company Email, or Personal Email
	employee = frappe.db.get_value("Employee", {"user_id": email}, "name")
	if not employee:
		employee = frappe.db.get_value("Employee", {"company_email": email}, "name")
	if not employee:
		employee = frappe.db.get_value("Employee", {"personal_email": email}, "name")

	if not employee:
		frappe.throw("Unable to process request.")

	existing_request = frappe.db.get_value("Mobile Access Request", {"employee": employee, "device_id": device_id, "status": "Pending"}, "name")
	if existing_request:
		existing_doc = frappe.get_doc("Mobile Access Request", existing_request)
		_auto_approve_if_test(existing_doc, email)
		return create_response(
			message="Access request already pending approval",
			data={
				"status": "pending",
				"request_name": existing_request,
			}
		)

	doc = frappe.new_doc("Mobile Access Request")
	doc.employee = employee
	doc.device_name = device_name
	doc.device_id = device_id
	doc.status = "Pending"
	doc.requested_on = now_datetime()
	doc.insert(ignore_permissions=True)

	_auto_approve_if_test(doc, email)

	return create_response(message="Request created successfully", data={"request_name": doc.name})

@frappe.whitelist(allow_guest=True)
def check_request_status(request_name, device_id):
    """
    Guest-safe polling endpoint.
    Delivers token ONCE and then clears it.
    """

    if not request_name or not device_id:
        return create_response(success=False, code=VALIDATION_ERROR, message="Invalid request")

    try:
        doc = frappe.get_doc("Mobile Access Request", request_name)
    except frappe.DoesNotExistError:
        return create_response(success=False, code=VALIDATION_ERROR, message="Invalid request")

    if doc.device_id != device_id:
        return create_response(success=False, code=VALIDATION_ERROR, message="Invalid request")

    data = {"status": doc.status}

    # Deliver token ONCE
    if doc.status == "Approved" and not doc.token_delivered:
        data.update({
            "erp_user": doc.erp_user,
            "api_key": doc.api_key,
            "api_secret": doc.get_password("api_secret"),
        })

        # Mark as delivered & wipe secret from request
        doc.db_set({
            "token_delivered": 1,
            "api_secret": None,
        }, update_modified=False)

    return create_response(data=data)