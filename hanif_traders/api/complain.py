# apps/hanif_traders/hanif_traders/api/complain.py
import frappe
from frappe.utils import today
from hanif_traders.api.technician_points import award_points_for_complain

@frappe.whitelist()
def verify_csc(complain_name, input_code):
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

    # Award points (idempotent)
    award_points_for_complain(complain_name, "CSC_VERIFIED")

    return {"ok": True, "message": f"{complain_name} marked 'CSC Verified' and points awarded."}

@frappe.whitelist()
def mark_resolved_without_csc(complain_name):
    complaint = frappe.get_doc("Complain", complain_name)
    if not complaint.assigned_to_technician:
        frappe.throw("Assigned Technician not set on this Complain")

    # If you need to change workflow/state, do it here:
    # complaint.db_set("workflow_state", "Resolved", update_modified=False)
    # complaint.db_set("resolution_date", today(), update_modified=False)

    from hanif_traders.api.technician_points import award_points_for_complain
    award_points_for_complain(complain_name, "RESOLVED_NO_CSC")

    return {"ok": True, "message": "Resolved without CSC; points awarded."}

@frappe.whitelist()
def process_incentive(complain_name):
    if not complain_name:
        frappe.throw("Complain name is required.")
    
    # Fetch the complain document
    complaint = frappe.get_doc("Complain", complain_name)
    tech = complaint.assigned_to_technician
    if not tech:
        frappe.throw("Assigned Technician not set on this Complain")
    
    #fetch complain settings
    settings = frappe.get_single("Complain Settings")
    limit = settings.incentive_start_limit
    amount = getattr(settings, "incentive_amount",0)
    incentive_account = settings.incentive_account
    if not amount:
        frappe.throw("Incentive amount is not set in Complain Settings.")
    if not limit:
        frappe.throw("Incentive limit is not set in Complain Settings.")
    
    # Count how many CSC-Verified complaints this tech has today
    count = frappe.db.count("Complain", {
        "assigned_to_technician": tech,
        "workflow_state": "CSC Verified",
        "resolution_date": today()
    })

    if count > limit:    
        # Create a Journal Entry to pay the incentive
        # Journal Entry Data
        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Journal Entry"
        je.posting_date = today()
        je.cheque_no = f"Incentive for Complain {complaint.name}"
        je.cheque_date = complaint.resolution_date or today()

        # Journal Entry Accounts Data
        # Debit
        je.append("accounts", {
            "account": incentive_account,
            "debit_in_account_currency": amount,
            "credit_in_account_currency": 0
        })

        # Credit
        je.append("accounts", {
            "account": "2110 - Creditors - acc",
            "party_type": "Employee",
            "party": tech,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": amount
        })

        je.insert(ignore_permissions=True)
        je.save()

        return (f"Incentive of {amount} posted for complaint #{count} today "
                f"(limit {limit}). JE: {je.name}")
    else:
        return f"No incentive: this is complaint #{count} today (limit {limit})."
        #return f"Incentive not posted for {complaint.name}, count is {count}."