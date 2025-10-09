import time, random
import frappe
from frappe.utils import today

POINTS_CSC_VERIFIED = 5
POINTS_RESOLVED_NO_CSC = 3

def _reason_points(reason_key: str) -> int:
    key = (reason_key or "").strip().upper()
    if key == "CSC_VERIFIED":
        return POINTS_CSC_VERIFIED
    if key == "RESOLVED_NO_CSC":
        return POINTS_RESOLVED_NO_CSC
    frappe.throw("Unknown reason")
    return 0  # not reached

def _retry_on_deadlock(fn, tries=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if e.__class__.__name__ != "QueryDeadlockError":
                raise
            frappe.db.rollback()
            time.sleep(0.12 * (i + 1) + random.random() * 0.12)
    return fn()

def _ensure_log(tech: str, complain: str, pts: int, reason_key: str) -> str:
    """Create a log row if not already present. Return the log name."""
    # Idempotency check (exact match on tech+complain+reason)
    existing = frappe.db.exists(
        "Technician Points Log",
        {"technician": tech, "complain": complain, "reason": reason_key},
    )
    if existing:
        return existing

    # Insert the log (ignore_permissions so tech perms don’t block)
    log = frappe.get_doc({
        "doctype": "Technician Points Log",
        "technician": tech,
        "complain": complain,
        "points": pts,
        "reason": reason_key,
        "posting_date": today(),
    })
    log.insert(ignore_permissions=True)
    return log.name

def _increment_total_points(tech: str, pts: int):
    # Atomic SQL update (no read→write race)
    frappe.db.sql(
        """UPDATE `tabEmployee`
           SET custom_total_points = COALESCE(custom_total_points, 0) + %(p)s
           WHERE name = %(t)s""",
        {"p": pts, "t": tech},
    )

@frappe.whitelist()
def award_points_for_complain(complain_name: str, reason: str):
    """Always creates a Technician Points Log (once per reason), then bumps total."""
    doc = frappe.get_doc("Complain", complain_name)
    tech = doc.assigned_to_technician
    if not tech:
        frappe.throw("Assigned Technician not set on this Complain")

    reason_key = (reason or "").strip().upper()
    pts = _reason_points(reason_key)

    def txn():
        # 1) Ensure there is a log row (insert if missing)
        log_name = _ensure_log(tech, complain_name, pts, reason_key)
        # 2) Increment running total
        _increment_total_points(tech, pts)
        # 3) Commit together
        frappe.db.commit()
        return log_name

    log_name = _retry_on_deadlock(txn)
    total = frappe.db.get_value("Employee", tech, "custom_total_points") or 0
    return {"ok": True, "log": log_name, "total": total, "message": f"{pts} points awarded"}