import frappe
from frappe.utils import now_datetime

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
		return {
			"status": "pending",
			"request_name": existing_request,
			"message": "Access request already pending approval",
		}

	doc = frappe.new_doc("Mobile Access Request")
	doc.employee = employee
	doc.device_name = device_name
	doc.device_id = device_id
	doc.status = "Pending"
	doc.requested_on = now_datetime()
	doc.insert(ignore_permissions=True)

	return {"message": "Request created successfully", "request_name": doc.name}

@frappe.whitelist(allow_guest=True)
def check_request_status(request_name, device_id):
    """
    Guest-safe polling endpoint.
    Delivers token ONCE and then clears it.
    """

    if not request_name or not device_id:
        frappe.throw("Invalid request")

    try:
        doc = frappe.get_doc("Mobile Access Request", request_name)
    except frappe.DoesNotExistError:
        frappe.throw("Invalid request")

    if doc.device_id != device_id:
        frappe.throw("Invalid request")

    response = {"status": doc.status}

    # Deliver token ONCE
    if doc.status == "Approved" and not doc.token_delivered:
        response.update({
            "erp_user": doc.erp_user,
            "api_key": doc.api_key,
            "api_secret": doc.get_password("api_secret"),
        })

        # Mark as delivered & wipe secret from request
        doc.db_set({
            "token_delivered": 1,
            "api_secret": None,
        }, update_modified=False)

    return response