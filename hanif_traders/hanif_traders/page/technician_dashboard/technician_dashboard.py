import frappe
from frappe.utils import nowdate, getdate, flt

@frappe.whitelist()
def get_dashboard_stats():
    # 1. Total Technicians (Active)
    active_employees = frappe.get_list("Employee", filters={"status": "Active"}, pluck="name")
    total_technicians = frappe.db.count("Technician", {"employee_id": ["in", active_employees]})

    # 2. Active Technicians (On Duty Today)
    today = nowdate()
    
    # Fetch all checkins for today
    employees_checked_in = frappe.db.sql("""
        SELECT employee, log_type FROM `tabEmployee Checkin`
        WHERE DATE(time) = %s
        ORDER BY time ASC
    """, (today,), as_dict=True)
    
    # Determine current status for each employee
    emp_status = {}
    for entry in employees_checked_in:
        emp_status[entry.employee] = entry.log_type
    
    active_count = sum(1 for status in emp_status.values() if status == 'IN')

    # 3. Complaints
    open_complaints = frappe.db.count("Complain", {
        "workflow_state": ["in", ["Open", "Pending", "Unresolved"]]
    })
    
    assigned_complaints = frappe.db.count("Complain", {
        "workflow_state": ["not in", ["Resolved", "Closed", "Rerouted", "Rejected", "CSC Verified"]],
        "assigned_to_technician": ["!=", ""]
    })

    # 4. Avg Resolution Time (Global - All Time)
    avg_res_time = frappe.db.sql("""
        SELECT AVG(time_to_resolution) FROM `tabComplain`
        WHERE workflow_state IN ('Resolved', 'Closed', 'CSC Verified')
        AND time_to_resolution > 0
    """)
    
    avg_res_val = avg_res_time[0][0] if avg_res_time and avg_res_time[0][0] else 0.0

    return {
        "total_technicians": total_technicians,
        "active_technicians": active_count,
        "open_complaints": open_complaints,
        "assigned_complaints": assigned_complaints,
        "avg_resolution_time": round(flt(avg_res_val), 2)
    }

@frappe.whitelist()
def get_leaderboard():
    # Top 10 by resolved complaints (All Time)
    data = frappe.db.sql("""
        SELECT t.technician_name as technician, COUNT(c.name) as count
        FROM `tabComplain` c
        JOIN `tabTechnician` t ON c.assigned_to_technician = t.name
        WHERE c.workflow_state IN ('Resolved', 'Closed', 'CSC Verified')
        GROUP BY c.assigned_to_technician
        ORDER BY count DESC
        LIMIT 10
    """, as_dict=True)
    
    return data
