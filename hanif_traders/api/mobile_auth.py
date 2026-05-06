import frappe
from frappe.utils import now_datetime
from hanif_traders.api.response import create_response, SUCCESS, UNAUTHORIZED, VALIDATION_ERROR

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