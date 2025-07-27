import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()
    data = []

    if not filters:
        filters = {}

    # Existing filters
    party_type      = filters.get("party_type")
    party           = filters.get("party")
    status          = filters.get("status")
    from_date       = getdate(filters.get("from_date")) if filters.get("from_date") else None
    to_date         = getdate(filters.get("to_date"))   if filters.get("to_date")   else None

    # New filters
    credit_account  = filters.get("credit_account")
    debit_account   = filters.get("debit_account")

    # Build the base WHERE conditions (for party, date, status, credit account)
    conditions = get_conditions(
        doc_alias="je",
        account_alias="jea",
        party_type=party_type,
        party=party,
        credit_account=credit_account,
        status=status,
        from_date=from_date,
        to_date=to_date
    )

    # Append the debit_account filter using an EXISTS subquery
    if debit_account:
        conditions += f""" AND EXISTS (
            SELECT 1 FROM `tabJournal Entry Account` debit_jea2
            WHERE debit_jea2.parent = je.name
              AND debit_jea2.debit > 0
              AND debit_jea2.account = {frappe.db.escape(debit_account)}
        )"""

    # Fetch only credit lines (existing logic), now with both filters applied
    journal_entries = frappe.db.sql(f"""
        SELECT
            je.posting_date,
            je.name,
            je.workflow_state AS status,
            jea.account,
            jea.party_type,
            jea.party,
            jea.party_name,
            CONCAT_WS(' | ', je.cheque_no, jea.user_remark) AS reference,
            jea.credit,
            (
                SELECT GROUP_CONCAT(
                    IF(
                        debit_jea.party IS NOT NULL AND debit_jea.party_name IS NOT NULL,
                        CONCAT(SUBSTRING_INDEX(debit_jea.account, ' - ', 1), ' (', debit_jea.party_name, ')'),
                        debit_jea.account
                    )
                    SEPARATOR ', '
                )
                FROM `tabJournal Entry Account` debit_jea
                WHERE debit_jea.parent = je.name AND debit_jea.debit > 0
            ) AS debited_to,
            'View' AS quick_view
        FROM
            `tabJournal Entry Account` jea
        INNER JOIN
            `tabJournal Entry` je ON je.name = jea.parent
        WHERE
            jea.credit > 0
            AND je.docstatus < 2
            {conditions}
        ORDER BY je.posting_date DESC
    """, as_dict=True)

    # Apply row styling based on status
    for row in journal_entries:
        if row.status == "Pending":
            row["__style"] = "background-color: #fff3cd;"
        elif row.status == "In Clearing":
            row["__style"] = "background-color: #d1ecf1;"
        elif row.status == "Returned":
            row["__style"] = "background-color: #f8d7da;"

    data.extend(journal_entries)
    return columns, data

def get_columns():
    return [
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Voucher No",    "fieldname": "name",         "fieldtype": "Link", "options": "Journal Entry", "width": 140},
        {"label": "Status",        "fieldname": "status",       "fieldtype": "Data", "width": 100},
        {"label": "Credit Account","fieldname": "account",      "fieldtype": "Link", "options": "Account", "width": 180},
        {"label": "Party Type",    "fieldname": "party_type",   "fieldtype": "Data", "width": 120},
        {"label": "Party",         "fieldname": "party",        "fieldtype": "Dynamic Link", "options": "party_type", "width": 140},
        {"label": "Party Name",    "fieldname": "party_name",   "fieldtype": "Data", "width": 140},
        {"label": "Credit",        "fieldname": "credit",       "fieldtype": "Currency", "width": 160},
        {"label": "Reference",     "fieldname": "reference",    "fieldtype": "Data", "width": 180},
        {"label": "Debit Account",    "fieldname": "debited_to",   "fieldtype": "Data", "width": 240},
        {"label": "Quick View",    "fieldname": "quick_view",   "fieldtype": "Data", "width": 100},
    ]

def get_conditions(doc_alias, account_alias, party_type, party, credit_account, status, from_date, to_date):
    conditions = []
    if party_type:
        conditions.append(f"{account_alias}.party_type = {frappe.db.escape(party_type)}")
    if party:
        conditions.append(f"{account_alias}.party = {frappe.db.escape(party)}")
    if credit_account:
        conditions.append(f"{account_alias}.account = {frappe.db.escape(credit_account)}")
    if status:
        conditions.append(f"{doc_alias}.workflow_state = {frappe.db.escape(status)}")
    if from_date:
        conditions.append(f"{doc_alias}.posting_date >= {frappe.db.escape(from_date)}")
    if to_date:
        conditions.append(f"{doc_alias}.posting_date <= {frappe.db.escape(to_date)}")

    return " AND " + " AND ".join(conditions) if conditions else ""