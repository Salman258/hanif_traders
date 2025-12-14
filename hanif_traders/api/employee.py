import frappe
from frappe.utils import getdate, today, date_diff

def calculate_age(doc, method):
    if doc.date_of_birth:
        dob = getdate(doc.date_of_birth)
        current_date = getdate(today())
        age = current_date.year - dob.year - ((current_date.month, current_date.day) < (dob.month, dob.day))
        doc.custom_age = age
