import frappe
from datetime import datetime, time
from frappe.utils import getdate, today, date_diff, now_datetime, add_to_date, get_datetime

def calculate_age(doc, method):
    if doc.date_of_birth:
        dob = getdate(doc.date_of_birth)
        current_date = getdate(today())
        age = current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day))
        doc.custom_age = age

def create_user_for_employee(employee):
    """
    Ensures the Employee has a User linked. Creates one if missing.
    Args:
        employee (str or Employee doc): Employee name or document.
    """
    if isinstance(employee, str):
        emp_doc = frappe.get_doc("Employee", employee)
    else:
        emp_doc = employee

    if emp_doc.user_id:
        return emp_doc.user_id

    # Determine email to use
    email = emp_doc.user_id or emp_doc.company_email or emp_doc.personal_email
    if not email:
        frappe.throw(f"Employee {emp_doc.name} has no email address to create a User.")

    # Check if User already exists (even if not linked)
    if frappe.db.exists("User", email):
        user_name = email
    else:
        # Create a new User
        user = frappe.new_doc("User")
        user.email = email
        user.first_name = emp_doc.employee_name or "Employee"
        user.enabled = 1
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
        user_name = user.name

    # Link User to Employee if not already linked
    if emp_doc.user_id != user_name:
        emp_doc.user_id = user_name
        emp_doc.save(ignore_permissions=True)

    return user_name

def sync_technician_details(doc, method):
    """
    Syncs Employee details to the linked Technician record on update.
    """
    # Check if a Technician is linked to this Employee
    tech_name = frappe.db.get_value("Technician", {"employee_id": doc.name}, "name")
    
    if tech_name:
        tech_doc = frappe.get_doc("Technician", tech_name)
        
        # Update fields
        tech_doc.cnic = doc.custom_cnic
        tech_doc.cnic_image = doc.custom_cnic_image
        tech_doc.phone_number = doc.custom_phone_number
        tech_doc.address = doc.current_address
        tech_doc.technician_name = doc.employee_name
        tech_doc.technician_age = doc.custom_age
        

        tech_doc.save(ignore_permissions=True)

@frappe.whitelist()
def employee_checkin(log_type, latitude=None, longitude=None, device_id=None):
    user = frappe.session.user
    if not user or user == "Guest":
         return {"status": "fail", "message": "Unauthorized"}
    
    employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee_name:
         # Try other emails if user_id match fails
         employee_name = frappe.db.get_value("Employee", {"company_email": user}, "name")
    if not employee_name:
         employee_name = frappe.db.get_value("Employee", {"personal_email": user}, "name")
         
    if not employee_name:
         return {"status": "fail", "message": "Employee not found for this user."}

    try:
        checkin = frappe.new_doc("Employee Checkin")
        checkin.employee = employee_name
        checkin.log_type = log_type
        checkin.time = now_datetime()
        checkin.device_id = device_id
        if latitude:
            checkin.latitude = latitude
        if longitude:
            checkin.longitude = longitude
        
        checkin.insert(ignore_permissions=True)
        return {"status": "success", "message": f"Checkin successful: {log_type}", "data": checkin.as_dict()}
    except Exception as e:
        frappe.log_error("Employee Checkin Error", str(e))
        return {"status": "fail", "message": str(e)}

@frappe.whitelist()
def auto_checkout_employees():
    """
    Auto check-out employees who forgot to check out yesterday.
    Runs daily.
    """
    current_date = getdate(today())
    
    # Get all employees
    employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")

    for emp in employees:
        last_log = frappe.db.get_value("Employee Checkin", 
            {"employee": emp}, 
            ["name", "log_type", "time"], 
            order_by="time desc",
            as_dict=True
        )

        if not last_log:
            continue
            
        # If last log was IN
        if last_log.log_type != "IN":
            continue
            
        log_date = getdate(last_log.time)
        
        # If the checkin was before today (any passed day), auto checkout them at that day's end
        if log_date < current_date:
            checkout_time = datetime.combine(log_date, time(23, 59, 59))
            
            checkout = frappe.new_doc("Employee Checkin")
            checkout.employee = emp
            checkout.log_type = "OUT"
            checkout.time = checkout_time
            checkout.device_id = "SYSTEM_AUTO_CHECKOUT"
            checkout.insert(ignore_permissions=True)
            
            frappe.logger().info(
                f"Auto checked out {emp} "
                f"(IN at {last_log.time}, OUT at {checkout_time})"
            )
    frappe.db.commit()


