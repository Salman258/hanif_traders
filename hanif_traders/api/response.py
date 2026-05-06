import frappe

# API Status Codes
SUCCESS = "SUCCESS"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
OFF_DUTY = "OFF_DUTY"
DUTY_EXPIRED = "DUTY_EXPIRED"
VALIDATION_ERROR = "VALIDATION_ERROR"
CONFLICT = "CONFLICT"
RATE_LIMITED = "RATE_LIMITED"
SERVER_ERROR = "SERVER_ERROR"

def create_response(success=True, code=SUCCESS, message="Operation completed successfully", data=None, meta=None):
    """
    Standard API Response Wrapper
    """
    response = {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "meta": meta or {}
    }
    return response

@frappe.whitelist()
def api_test():
    """ Test endpoint to verify standard response structure """
    return create_response(success=True, code=SUCCESS, message="API is working", data={"status": "live"})
