# apps/hanif_traders/hanif_traders/api/complain.py
import frappe
from frappe.utils import today
from frappe.utils import time_diff_in_hours, now_datetime, get_datetime
from hanif_traders.api.response import create_response, SUCCESS, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, VALIDATION_ERROR, SERVER_ERROR

@frappe.whitelist()
def verify_csc(complain_name, input_code):
    user = frappe.session.user
    if not user or user == "Guest":
        return create_response(success=False, code=UNAUTHORIZED, message="Authentication required")

    complaint = frappe.get_doc("Complain", complain_name)
    tech = complaint.assigned_to_technician
    if not tech:
        frappe.throw("Assigned Technician not set on this Complain")
    if not complaint.complain_csc:
        frappe.throw("CSC code has not been generated yet.")
    if complaint.complain_csc != input_code:
        frappe.throw("Invalid CSC code.")

    # Update state/fields
    complaint.db_set("workflow_state", "CSC Verified", update_modified=False)
    complaint.db_set("resolution_date", today(), update_modified=False)
    
    # Calculate time to resolution
    if complaint.date and complaint.posting_time:
        start_time = get_datetime(f"{complaint.date} {complaint.posting_time}")
    else:
        start_time = complaint.creation

    time_taken = round(time_diff_in_hours(now_datetime(), start_time), 2)

    frappe.db.set_value("Complain", complain_name, "time_to_resolution", time_taken, update_modified=False)

    # Process Incentives
    from hanif_traders.api.technician import process_incentive, update_avg_resolution_time
    msg = process_incentive(complain_name, "CSC_VERIFIED")
    
    # Update Avg Resolution Time
    update_avg_resolution_time(tech)

    return create_response(message=f"{complain_name} marked 'CSC Verified'. {msg}")

@frappe.whitelist()
def mark_resolved_without_csc(complain_name):
    user = frappe.session.user
    if not user or user == "Guest":
        return create_response(success=False, code=UNAUTHORIZED, message="Authentication required")

    complaint = frappe.get_doc("Complain", complain_name)
    if not complaint.assigned_to_technician:
        frappe.throw("Assigned Technician not set on this Complain")

    complaint.db_set("workflow_state", "Resolved", update_modified=False)
    complaint.db_set("resolution_date", today(), update_modified=False)

    # Process Incentives
    from hanif_traders.api.technician import process_incentive, update_avg_resolution_time
    msg = process_incentive(complain_name, "RESOLVED_NO_CSC")
    
    # Update Avg Resolution Time
    update_avg_resolution_time(complaint.assigned_to_technician)
    update_avg_resolution_time(complaint.assigned_to_technician)
    return create_response(message=f"Resolved without CSC. {msg}")

@frappe.whitelist()
def bulk_assign(complain_names, technician):
    user = frappe.session.user
    if not user or user == "Guest":
        return create_response(success=False, code=UNAUTHORIZED, message="Authentication required")

    import json
    if isinstance(complain_names, str):
        complain_names = json.loads(complain_names)
    
    if not complain_names or not technician:
        frappe.throw("Complain names and Technician are required.")

    success_count = 0
    errors = []

    for name in complain_names:
        try:
            doc = frappe.get_doc("Complain", name)
            if doc.workflow_state == "Open":
                doc.assigned_to_technician = technician
                doc.workflow_state = "Assigned"
                doc.save() # This will trigger on_update and send SMS
                success_count += 1
        except Exception as e:
            frappe.log_error(title=f"Bulk Assign Error: {name}", message=frappe.get_traceback())
            errors.append(f"{name}: {str(e)}")
    
    msg = f"{success_count} complaints assigned."
    if errors:
        msg += f" {len(errors)} failed (check Error Log)."
    
    msg = f"{success_count} complaints assigned."
    if errors:
        msg += f" {len(errors)} failed (check Error Log)."
    
    return create_response(message=msg)

@frappe.whitelist()
def get_complains(status=None):
    user = frappe.session.user
    if not user or user == "Guest":
        return create_response(success=False, code=UNAUTHORIZED, message="Authentication required")
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    technician = frappe.db.get_value("Technician", {"employee_id": employee}, "name")

    filters = {}
    
    if status != "Open":
        filters["assigned_to_technician"] = technician

    if status:
        if isinstance(status, list):
            filters["workflow_state"] = ["in", status]
        else:
            filters["workflow_state"] = status

    complains = frappe.get_all(
        "Complain",
        filters=filters,
        fields=["*"]
    )

    for complain in complains:
        if "complain_csc" in complain:
            del complain["complain_csc"]
            
    return create_response(data=complains)

@frappe.whitelist()
def get_complain_count(status=None):
    user = frappe.session.user
    if not user or user == "Guest":
        return create_response(success=False, code=UNAUTHORIZED, message="Authentication required")
    
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    technician = frappe.db.get_value("Technician", {"employee_id": employee}, "name")

    filters = {}
    
    if status != "Open":
        filters["assigned_to_technician"] = technician

    if status:
        if isinstance(status, list):
            filters["workflow_state"] = ["in", status]
        else:
            filters["workflow_state"] = status

    count = frappe.db.count("Complain", filters=filters)
    return create_response(data=count, meta={"count": count})