# hanif_traders/hanif_traders/doctype/technician_points_redemption/technician_points_redemption.py

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class TechnicianPointsRedemption(Document):
    """Redemption request lifecycle:
       Draft -> (approve_redemption) -> Approved -> (mark_paid) -> Paid
       Or Draft/Approved -> (reject_redemption) -> Rejected
    """

    def validate(self):
        # Coerce numbers
        self.points_to_redeem = int(self.points_to_redeem or 0)
        self.value_per_point = flt(self.value_per_point or 0)

        # Pull default value_per_point from Complain Settings if not set
        if not self.value_per_point:
            self.value_per_point = flt(
                frappe.db.get_single_value("Complain Settings", "point_value") or 0
            )

        # Compute total_value
        self.total_value = flt(self.points_to_redeem * self.value_per_point)

        # Basic checks
        if not self.technician:
            frappe.throw("Please select a Technician (Employee).")

        if self.points_to_redeem <= 0:
            frappe.throw("Points to Redeem must be greater than zero.")

        # Status guardrails
        if not self.status:
            self.status = "Draft"

        if self.status not in ("Draft", "Approved", "Rejected", "Paid"):
            frappe.throw("Invalid status. Must be Draft / Approved / Rejected / Paid.")

    # (No automatic deduction here: we do it in the approve action below)


# -------- Utilities -------- #

def _get_available_points(emp: str) -> int:
    return int(frappe.db.get_value("Employee", emp, "custom_total_points") or 0)


def _atomic_deduct_points(emp: str, points: int):
    """Atomic SQL decrement to avoid read-then-write races."""
    if points <= 0:
        return
    frappe.db.sql(
        """
        UPDATE `tabEmployee`
        SET custom_total_points = GREATEST(COALESCE(custom_total_points, 0) - %(pts)s, 0)
        WHERE name = %(emp)s
        """,
        {"pts": points, "emp": emp},
    )


def _make_journal_entry(emp: str, amount: float, posting_date: str) -> str:
    """Create a simple JE crediting Employee (as Creditors) and debiting Incentive Expense account.
       Configure accounts in Complain Settings.
    """
    settings = frappe.get_single("Complain Settings")
    expense_acc = getattr(settings, "incentive_expense_account", None)
    payable_acc = getattr(settings, "incentive_payable_account", None)

    if not expense_acc or not payable_acc:
        frappe.throw("Please set Incentive Expense and Payable accounts in Complain Settings.")

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "posting_date": posting_date or today(),
        "accounts": [
            {
                "account": expense_acc,
                "debit_in_account_currency": flt(amount),
                "credit_in_account_currency": 0,
            },
            {
                "account": payable_acc,
                "party_type": "Employee",
                "party": emp,
                "debit_in_account_currency": 0,
                "credit_in_account_currency": flt(amount),
            },
        ],
        "user_remark": "Technician Points Redemption",
    })
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


# -------- Actions (whitelisted) -------- #

@frappe.whitelist()
def approve_redemption(name: str):
    """Approve a Draft redemption:
       - checks available points
       - deducts points atomically
       - sets status=Approved, redeemed_on=today
    """
    doc = frappe.get_doc("Technician Points Redemption", name)
    if doc.status not in ("Draft",):
        frappe.throw(f"Only Draft can be approved. Current status: {doc.status}")

    available = _get_available_points(doc.technician)
    if doc.points_to_redeem > available:
        frappe.throw(f"Not enough points. Available: {available}, requested: {doc.points_to_redeem}")

    # Deduct atomically, then mark approved
    _atomic_deduct_points(doc.technician, doc.points_to_redeem)

    doc.db_set("status", "Approved", update_modified=False)
    doc.db_set("redeemed_on", today(), update_modified=False)
    frappe.db.commit()

    return {"ok": True, "message": f"Approved. Deducted {doc.points_to_redeem} points."}


@frappe.whitelist()
def reject_redemption(name: str, reason: str | None = None):
    """Reject a Draft/Approved redemption. No points are refunded here.
       (If you want to refund on reject-from-Approved, add logic to add back points.)
    """
    doc = frappe.get_doc("Technician Points Redemption", name)
    if doc.status not in ("Draft", "Approved"):
        frappe.throw(f"Only Draft/Approved can be rejected. Current status: {doc.status}")
    doc.db_set("status", "Rejected", update_modified=False)
    if reason:
        doc.db_set("remarks", (doc.remarks or "") + f"\nRejected: {reason}", update_modified=False)
    frappe.db.commit()
    return {"ok": True, "message": "Redemption rejected."}


@frappe.whitelist()
def mark_paid(name: str, create_journal_entry: int = 1):
    """Mark an Approved redemption as Paid, optionally creating a Journal Entry."""
    doc = frappe.get_doc("Technician Points Redemption", name)
    if doc.status != "Approved":
        frappe.throw(f"Only Approved redemptions can be marked Paid. Current status: {doc.status}")

    je_name = None
    if int(create_journal_entry or 0) == 1:
        je_name = _make_journal_entry(
            emp=doc.technician,
            amount=flt(doc.total_value or 0),
            posting_date=doc.redeemed_on or today(),
        )
        doc.db_set("journal_entry", je_name, update_modified=False)

    doc.db_set("status", "Paid", update_modified=False)
    frappe.db.commit()
    return {"ok": True, "message": "Marked as Paid.", "journal_entry": je_name}