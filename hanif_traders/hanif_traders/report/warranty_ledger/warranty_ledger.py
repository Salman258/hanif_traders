import frappe
from frappe.utils import getdate

def execute(filters=None):
    filters = filters or {}
    from_date   = getdate(filters.get("from_date")) if filters.get("from_date") else None
    to_date     = getdate(filters.get("to_date"))   if filters.get("to_date")   else None
    customer    = filters.get("customer")
    item_code   = filters.get("item_code")
    item_group  = filters.get("item_group")
    group_by_item = filters.get("group_by_item")

    # build where clauses dynamically
    conditions = ["w.docstatus=1"]
    args = {}

    if from_date:
        conditions.append("w.date >= %(from_date)s")
        args["from_date"] = from_date
    if to_date:
        conditions.append("w.date <= %(to_date)s")
        args["to_date"] = to_date
    if customer:
        conditions.append("w.customer = %(customer)s")
        args["customer"] = customer
    if item_code:
        conditions.append("wi.item_code = %(item_code)s")
        args["item_code"] = item_code
    if item_group:
        conditions.append("i.item_group = %(item_group)s")
        args["item_group"] = item_group

    where = " AND ".join(conditions)

    # ---------------------------------------------
    # GROUPED BY ITEM
    # ---------------------------------------------
    if group_by_item:
        data = frappe.db.sql(f"""
            SELECT
                wi.item_code,
                wi.item_name,
                wi.replacement_item,
                SUM(wi.replacement_quantity) AS total_replacement,
                SUM(wi.quantity_received) AS total_received,
                SUM(wi.quantity_claimed) AS total_claimed,
                SUM(wi.balance_quantity) AS total_balance,
                w.customer,
                c.customer_name
            FROM `tabWarranty` w
            JOIN `tabwarranty item` wi
              ON wi.parent = w.name
            LEFT JOIN `tabItem` i
              ON i.name = wi.item_code
            LEFT JOIN `tabCustomer` c
              ON c.name = w.customer
            WHERE {where}
            GROUP BY wi.item_code, wi.item_name, w.customer, c.customer_name
            ORDER BY wi.item_code
        """, args, as_dict=True)

        columns = [
            {"label":"Item Code",       "fieldname":"item_code",      "fieldtype":"Link", "options":"Item",     "width":120},
            {"label":"Item Name",       "fieldname":"item_name",      "fieldtype":"Data",               "width":180},
            {"label":"Total Received",  "fieldname":"total_received", "fieldtype":"Float",              "width":100},
            {"label":"Total Claimed",   "fieldname":"total_claimed",  "fieldtype":"Float",              "width":100},
            {"label":"Replacement Item",   "fieldname":"replacement_item",  "fieldtype":"Data",              "width":100},
            {"label":"Total Replacement",   "fieldname":"total_replacement",  "fieldtype":"Float",              "width":100},
            {"label":"Total Balance",   "fieldname":"total_balance",  "fieldtype":"Float",              "width":100},
        ]

        return columns, data, None, filters

    # ---------------------------------------------
    # DETAILED ROWS (NO GROUPING)
    # ---------------------------------------------
    else:
        data = frappe.db.sql(f"""
            SELECT
                w.name            AS warranty_no,
                w.date            AS warranty_date,
                w.customer,
                c.customer_name,
                wi.item_code,
                wi.item_name,
                wi.replacement_item,
                wi.replacement_quantity,
                wi.quantity_received AS qty_received,
                wi.quantity_claimed  AS qty_claimed,
                wi.balance_quantity  AS balance_qty
            FROM `tabWarranty` w
            JOIN `tabwarranty item` wi
              ON wi.parent = w.name
            LEFT JOIN `tabItem` i
              ON i.name = wi.item_code
            LEFT JOIN `tabCustomer` c
              ON c.name = w.customer
            WHERE {where}
            ORDER BY w.date, w.name, wi.idx
        """, args, as_dict=True)

        columns = [
            {"label":"Warranty#",       "fieldname":"warranty_no",    "fieldtype":"Link", "options":"Warranty", "width":100},
            {"label":"Date",            "fieldname":"warranty_date",  "fieldtype":"Date",               "width":90},
            {"label":"Customer",        "fieldname":"customer_name",  "fieldtype":"Data",               "width":160},
            {"label":"Item Code",       "fieldname":"item_code",      "fieldtype":"Link", "options":"Item",     "width":100},
            {"label":"Item Name",       "fieldname":"item_name",      "fieldtype":"Data",               "width":140},
            {"label":"Received",        "fieldname":"qty_received",   "fieldtype":"Float",              "width":80},
            {"label":"Claimed",         "fieldname":"qty_claimed",    "fieldtype":"Float",              "width":80},
            {"label":"Replacement Item", "fieldname":"replacement_item", "fieldtype":"Data",              "width":100},
            {"label":"Replacement Qty", "fieldname":"replacement_quantity", "fieldtype":"Float",              "width":80},
            {"label":"Balance",         "fieldname":"balance_qty",    "fieldtype":"Float",              "width":80},
        ]

        return columns, data, None, filters