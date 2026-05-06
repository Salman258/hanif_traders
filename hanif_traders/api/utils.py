import frappe

from hanif_traders.api.response import create_response, SUCCESS, SERVER_ERROR

@frappe.whitelist()
def log_error(title, message):
    try:
        frappe.log_error(title=title, message=message)
        return create_response(message="Error logged successfully")
    except Exception as e:
        return create_response(success=False, code=SERVER_ERROR, message=str(e))

@frappe.whitelist()
def create_activity_log():
    #TODO: Create activity log using activity log doctype   
    return create_response(message="Activity log created")

def create_stock_entry():
    # TODO : Create General Purpose Stock Entry for use by App Doctypes
    pass

def create_journal_entry():
    # TODO : Create General Purpose Journal Entry for use by App Doctypes
    pass

def send_sms():
    # TODO : App Wrapper for frappe.core.doctype.sms_settings.sms_settings import send_sms
    pass