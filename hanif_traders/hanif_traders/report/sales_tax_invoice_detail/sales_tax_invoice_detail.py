import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
        {"label": "Customer Tax ID", "fieldname": "tax_id", "fieldtype": "Data", "width": 150},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
        {"label": "Invoice No.", "fieldname": "invoice_no", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Customs Tariff Number", "fieldname": "customs_tariff_number", "fieldtype": "Data", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Quantity", "fieldname": "total_qty", "fieldtype": "Float", "width": 100},
        {"label": "Value Excluding Sales Tax", "fieldname": "base_net_amount", "fieldtype": "Currency", "width": 160},
        {"label": "Value of Sales Tax", "fieldname": "sales_tax", "fieldtype": "Currency", "width": 160}
    ]

def get_data(filters):
    group_by_tariff = filters.get("group_by_tariff")

    conditions = ["si.docstatus = 0"]

    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")

    if filters.get("company"):
        conditions.append("si.company = %(company)s")

    condition_clause = " AND ".join(conditions)

    if group_by_tariff:
        return frappe.db.sql("""
            SELECT
                c.tax_id AS tax_id,
                si.customer_name AS customer_name,
                si.name AS invoice_no,
                si.posting_date AS posting_date,
                i.customs_tariff_number AS customs_tariff_number,
                NULL AS item_name,
                SUM(sii.qty) AS total_qty,
                SUM(sii.base_net_amount) AS base_net_amount,
                SUM(sii.base_amount - sii.base_net_amount) AS sales_tax
            FROM
                `tabSales Invoice` si
            JOIN
                `tabSales Invoice Item` sii ON sii.parent = si.name
            LEFT JOIN
                `tabItem` i ON i.name = sii.item_code
            JOIN
                `tabCustomer` c ON c.name = si.customer
            WHERE
                {condition_clause}
            GROUP BY
                si.name, i.customs_tariff_number
            ORDER BY
                si.posting_date DESC
        """.format(condition_clause=condition_clause), filters, as_dict=True)
    else:
        return frappe.db.sql("""
            SELECT
                c.tax_id AS tax_id,
                si.customer_name AS customer_name,
                si.name AS invoice_no,
                si.posting_date AS posting_date,
                i.customs_tariff_number AS customs_tariff_number,
                sii.item_name AS item_name,
                sii.qty AS total_qty,
                sii.base_net_amount AS base_net_amount,
                (sii.base_amount - sii.base_net_amount) AS sales_tax
            FROM
                `tabSales Invoice` si
            JOIN
                `tabSales Invoice Item` sii ON sii.parent = si.name
            LEFT JOIN
                `tabItem` i ON i.name = sii.item_code
            JOIN
                `tabCustomer` c ON c.name = si.customer
            WHERE
                {condition_clause}
            ORDER BY
                si.posting_date DESC
        """.format(condition_clause=condition_clause), filters, as_dict=True)
