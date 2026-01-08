import frappe
from frappe.utils import now_datetime, get_datetime, getdate
from datetime import datetime, time

@frappe.whitelist(methods=["POST"])
def ingest(latitude, longitude, accuracy=None, speed=None, heading=None, altitude=None, captured_at=None, device_id=None, source="foreground"):
    """
    Ingest a single GPS telemetry point.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"status": "fail", "message": "Unauthorized"}

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except Exception:
        return {"status": "fail", "message": "Invalid latitude/longitude"}

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return {"status": "fail", "message": "Coordinates out of range"}

    # 1. Resolve Identity
    employee = (
        frappe.db.get_value("Employee", {"user_id": user}, "name")
        or frappe.db.get_value("Employee", {"company_email": user}, "name")
        or frappe.db.get_value("Employee", {"personal_email": user}, "name")
    )
    
    if not employee:
        return {"status": "fail", "message": "Employee not found"}

    technician = frappe.db.get_value("Technician", {"employee_id": employee}, "name")
    if not technician:
         return {"status": "fail", "message": "Technician not found"}

    # 2. Verify Duty State
    # We need the active checkin to link it.
    last_checkin = frappe.db.get_value("Employee Checkin", 
        {"employee": employee}, 
        ["name", "log_type", "time"], 
        order_by="time desc",
        as_dict=True
    )

    if not last_checkin or last_checkin.log_type != "IN":
        return {"status": "fail", "message": "Technician is OFF DUTY"}

    if getdate(last_checkin.time) != getdate(now_datetime()):
        return {"status": "fail", "message": "Duty expired. Please check in again."}

    if captured_at:
        try:
            captured_at = frappe.utils.get_datetime(captured_at)
            # Reject future timestamps
            if captured_at > now_datetime():
                captured_at = now_datetime()
        except Exception:
            captured_at = now_datetime()
    else:
        captured_at = now_datetime()
    # 3. Insert Log
    try:
        log = frappe.new_doc("Technician Location Log")
        log.technician = technician
        log.employee = employee
        log.employee_checkin = last_checkin.name
        log.device_id = device_id
        log.source = source
        log.latitude = latitude
        log.longitude = longitude
        if accuracy is not None:
            log.accuracy = accuracy
        if speed is not None:
            log.speed = speed
        if heading is not None:
            log.heading = heading
        if altitude is not None:
            log.altitude = altitude
        
        log.captured_at = captured_at
        log.received_at = now_datetime()
        
        log.insert(ignore_permissions=True)
        
        return {"status": "success"}

    except Exception as e:
        frappe.log_error(
            title="Location Ingest Error",
            message=frappe.get_traceback(),
        )
        return {"status": "fail", "message": "Internal Server Error"}

@frappe.whitelist()
def get_latest_locations(on_duty_only=True):
    """
    Get the last known location of technicians.
    """
    # Role check could be added here if needed
    today = getdate(now_datetime())
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    results = []

    checkin_filters = {
        "log_type": "IN",
        "time": ["between", [start_of_day, end_of_day]]
    }
    active_checkins = frappe.get_all(
        "Employee Checkin",
        filters=checkin_filters,
        fields=["name", "employee", "time"],
        order_by="time desc",
    )

    active_checkin_map = {}

    for ci in active_checkins:
        # Since ordered by DESC, the first one encountered is the latest
        if ci.employee not in active_checkin_map:
            active_checkin_map[ci.employee] = ci.name

    if on_duty_only and not active_checkin_map:
        return {"status": "success", "data": []}

    tech_filters = {}
    if on_duty_only:
        tech_filters["employee_id"] = ["in", list(active_checkin_map.keys())]
    
    technicians = frappe.get_all("Technician", fields=["name", "employee_id", "technician_name"], filters=tech_filters)

    for tech in technicians:
        checkin_name = active_checkin_map.get(tech.employee_id)

        if on_duty_only and not checkin_name:
            continue
            
        loc_filters = {"technician": tech.name}
        if on_duty_only:
             # Strict: Only show location from CURRENT active shift
             loc_filters["employee_checkin"] = checkin_name

        last_loc = frappe.db.get_value(
            "Technician Location Log",
            loc_filters,
            ["latitude", "longitude", "captured_at"],
            order_by="captured_at desc",
            as_dict=True,
        )

        if last_loc:
            results.append({
                "technician": tech.name,
                "technician_name": tech.technician_name,
                "latitude": last_loc.latitude,
                "longitude": last_loc.longitude,
                "captured_at": last_loc.captured_at,
            })
            
    return {"status": "success", "data": results}

@frappe.whitelist()
def get_route(technician, date=None, employee_checkin=None):
    """
    Get ordered route points.
    """
    filters = {"technician": technician}
    
    if employee_checkin:
        filters["employee_checkin"] = employee_checkin
    elif date:
        # Filter by date range `captured_at`
        filters["captured_at"] = ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
    
    points = frappe.get_all("Technician Location Log",
        filters=filters,
        fields=["latitude", "longitude", "captured_at", "speed", "heading"],
        order_by="captured_at asc",
        limit=5000 
    )
    
    return {"status": "success", "data": points}

@frappe.whitelist()
def get_distance_summary(technician=None, period=None):
    """
    Placeholder for pre-computed distance summary.
    """
    # This implies a separate summary table exists or we compute on fly.
    # Instruction says "No live computation".
    # Since we haven't built the summarizer yet, return empty.
    
    return {"status": "success", "data": []}
