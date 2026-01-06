import frappe
from frappe.utils import getdate, today, date_diff

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
