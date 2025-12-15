import frappe
from frappe.utils import today, flt

def process_incentive(complain_name, reason):
    complaint = frappe.get_doc("Complain", complain_name)
    tech_name = complaint.assigned_to_technician
    if not tech_name:
        return

    settings = frappe.get_single("Complain Settings")
    
    try:
        # Check Start Limit (Global)
        today_count = frappe.db.count("Complain", {
            "assigned_to_technician": tech_name,
            "workflow_state": ["in", ["CSC Verified", "Resolved"]],
            "resolution_date": today()
        })

        limit = settings.incentive_start_limit or 0
        if today_count <= limit:
            return f"No incentive: This is complaint #{today_count} today (Limit: {limit})."

        messages = []

        # 1. Currency Incentive
        if settings.enable_currency_incentive:
            msg = _process_currency_incentive(complaint, tech_name, settings, reason)
            if msg: messages.append(msg)

        # 2. Point Incentive
        if settings.enable_point_incentive:
            msg = _process_point_incentive(complaint, tech_name, settings, reason)
            if msg: messages.append(msg)

        return "\n".join(messages)
    except Exception as e:
        frappe.log_error(title="Incentive Processing Error", message=frappe.get_traceback())
        return f"Error processing incentive: {str(e)}"

def _process_currency_incentive(complaint, tech_name, settings, reason):
    amount = 0
    if reason == "CSC_VERIFIED":
        amount = flt(settings.amount_on_csc_verified)
    elif reason == "RESOLVED_NO_CSC":
        amount = flt(settings.amount_on_resolved)

    if amount <= 0:
        return None

    # Check Max Incentive Per Day
    max_daily = flt(settings.max_incentive_per_day)
    if max_daily > 0:
        current_daily_total = _get_today_currency_incentive(tech_name)
        if (current_daily_total + amount) > max_daily:
            return f"Currency Incentive Skipped: Daily limit reached ({current_daily_total} + {amount} > {max_daily})."

    # Create Journal Entry
    payable_account = settings.incentive_payable_account
    
    if not payable_account:
        return "Currency Incentive Error: Accounts not set in settings."

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = today()
    je.cheque_no = f"Incentive for Complain {complaint.name}"
    je.cheque_date = complaint.resolution_date or today()
    je.user_remark = f"Incentive for {complaint.name} ({reason})"

    # Debit Expense
    je.append("accounts", {
        "account": payable_account,
        "debit_in_account_currency": amount,
        "credit_in_account_currency": 0,
        "cost_center": frappe.get_cached_value('Company', settings.company, 'cost_center') if settings.company else None
    })

    # Credit Payable (Employee/Technician)
    je.append("accounts", {
        "account": "2110 - Creditors - acc",
        "party_type": "Employee",
        "party": tech_name, # Technician name is Employee ID
        "debit_in_account_currency": 0,
        "credit_in_account_currency": amount
    })

    je.insert(ignore_permissions=True)
    je.save()
    je.submit() 

    # Update Technician Record
    _update_technician_currency(tech_name, amount)

    return f"Currency Incentive: {amount} posted (JE: {je.name})."

def _process_point_incentive(complaint, tech_name, settings, reason):
    points = 0
    if reason == "CSC_VERIFIED":
        points = int(settings.point_on_csc_verified)
    elif reason == "RESOLVED_NO_CSC":
        points = int(settings.point_on_resolved)
    
    if points <= 0:
        return None

    # Check Max Points Per Day
    max_daily = int(settings.max_point_per_day)
    if max_daily > 0:
        current_daily_points = _get_today_points(tech_name)
        if (current_daily_points + points) > max_daily:
            return f"Point Incentive Skipped: Daily limit reached ({current_daily_points} + {points} > {max_daily})."

    # Create Log
    log = frappe.get_doc({
        "doctype": "Technician Points Log",
        "technician": tech_name,
        "complain": complaint.name,
        "points": points,
        "reason": reason,
        "posting_date": today(),
    })
    log.insert(ignore_permissions=True)

    # Update Technician Record
    _update_technician_points(tech_name, points)

    return f"Point Incentive: {points} points awarded."

def _get_today_currency_incentive(tech_name):
    # Sum credits to the employee in the payable account for today
    creditor_account = "2110 - Creditors - acc"
    data = frappe.db.sql("""
        SELECT SUM(credit_in_account_currency)
        FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON jea.parent = je.name
        WHERE je.posting_date = %s
        AND jea.account = %s
        AND jea.party_type = 'Employee'
        AND jea.party = %s
        AND je.docstatus = 1
    """, (today(), creditor_account, tech_name))
    
    return flt(data[0][0]) if data else 0.0

def _get_today_points(tech_name):
    data = frappe.db.sql("""
        SELECT SUM(points)
        FROM `tabTechnician Points Log`
        WHERE technician = %s
        AND posting_date = %s
    """, (tech_name, today()))
    
    return flt(data[0][0]) if data else 0.0

def _update_technician_currency(tech_name, amount):
    # Update incentive_earned in Technician
    frappe.db.sql("""
        UPDATE `tabTechnician`
        SET incentive_earned = COALESCE(incentive_earned, 0) + %s
        WHERE name = %s
    """, (amount, tech_name))

def _update_technician_points(tech_name, points):
    # Update technician_points in Technician
    frappe.db.sql("""
        UPDATE `tabTechnician`
        SET technician_points = COALESCE(technician_points, 0) + %s
        WHERE name = %s
    """, (points, tech_name))