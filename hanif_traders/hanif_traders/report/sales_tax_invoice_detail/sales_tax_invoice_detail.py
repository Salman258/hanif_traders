import frappe

# Prefix match so company suffixes like " - HT" don't break it
GST_ACCOUNT_PREFIX = "GST - F&C"
DISCOUNT_ACCOUNT_PREFIX = "5224 - Discount Allowed - F&C"

def execute(filters=None):
    filters = filters or {}

    # Bind account filters safely
    filters["gst_account_like"] = f"{GST_ACCOUNT_PREFIX}%"
    filters["discount_account_like"] = f"{DISCOUNT_ACCOUNT_PREFIX}%"

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

        # Net goods value AFTER prorated invoice-level discount (no sales tax)
        {"label": "Value Excluding Sales Tax", "fieldname": "base_net_amount", "fieldtype": "Currency", "width": 180},

        # GST amount (prorated from invoice GST)
        {"label": "Value of Sales Tax", "fieldname": "sales_tax", "fieldtype": "Currency", "width": 160},

        # Pure net goods value (no sales tax, no discount)
        {"label": "Fixed Value", "fieldname": "fixed_value", "fieldtype": "Currency", "width": 160},
    ]

def get_data(filters):
    group_by_tariff = cint_bool(filters.get("group_by_tariff"))

    # --- Conditions ---
    conditions = ["si.docstatus = 1"]  # Only submitted invoices
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
    if filters.get("company"):
        conditions.append("si.company = %(company)s")
    if filters.get("customer"):
        conditions.append("si.customer = %(customer)s")
    condition_clause = " AND ".join(conditions)

    # --- Invoice-level GST and Discount (from Taxes & Charges) ---
    taxes_subquery = """
        SELECT
            stc.parent AS invoice,
            SUM(
                CASE WHEN stc.account_head LIKE %(gst_account_like)s
                     THEN stc.base_tax_amount ELSE 0 END
            ) AS inv_sales_tax,
            SUM(
                CASE WHEN stc.account_head LIKE %(discount_account_like)s
                     THEN ABS(stc.base_tax_amount) ELSE 0 END
            ) AS inv_discount
        FROM `tabSales Taxes and Charges` stc
        WHERE stc.parenttype = 'Sales Invoice'
        GROUP BY stc.parent
    """

    # --- Invoice net total (sum of item base_net_amount) for proration ---
    totals_subquery = """
        SELECT
            sii.parent AS invoice,
            SUM(sii.base_net_amount) AS inv_net_total
        FROM `tabSales Invoice Item` sii
        GROUP BY sii.parent
    """

    if group_by_tariff:
        # One row per (invoice, HS code)
        return frappe.db.sql(f"""
            SELECT
                c.tax_id AS tax_id,
                si.customer_name AS customer_name,
                si.name AS invoice_no,
                si.posting_date AS posting_date,
                COALESCE(i.customs_tariff_number, '') AS customs_tariff_number,
                NULL AS item_name,
                SUM(sii.qty) AS total_qty,

                /* Group net before invoice-level discount */
                SUM(sii.base_net_amount) AS group_net,

                /* Share of invoice net */
                COALESCE(SUM(sii.base_net_amount) / NULLIF(tot.inv_net_total, 0), 0) AS pct_share,

                /* Value Excl ST = group_net - (invoice_discount * share) */
                (SUM(sii.base_net_amount)
                 - COALESCE(tx.inv_discount, 0) * COALESCE(SUM(sii.base_net_amount) / NULLIF(tot.inv_net_total, 0), 0)
                ) AS base_net_amount,

                /* Sales Tax (group share of invoice GST) */
                (COALESCE(tx.inv_sales_tax, 0)
                 * COALESCE(SUM(sii.base_net_amount) / NULLIF(tot.inv_net_total, 0), 0)
                ) AS sales_tax,

                /* Fixed Value = pure net (no ST, no discount) */
                SUM(sii.base_net_amount) AS fixed_value

            FROM `tabSales Invoice` si
            JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
            LEFT JOIN `tabItem` i ON i.name = sii.item_code
            JOIN `tabCustomer` c ON c.name = si.customer
            LEFT JOIN ({taxes_subquery}) tx ON tx.invoice = si.name
            LEFT JOIN ({totals_subquery}) tot ON tot.invoice = si.name
            WHERE {condition_clause}
            GROUP BY si.name, COALESCE(i.customs_tariff_number, ''), c.tax_id, si.customer_name,
                     si.posting_date, tot.inv_net_total, tx.inv_sales_tax, tx.inv_discount
            ORDER BY si.posting_date DESC, si.name DESC
        """, filters, as_dict=True)
    else:
        # Detail rows (per item)
        return frappe.db.sql(f"""
            SELECT
                c.tax_id AS tax_id,
                si.customer_name AS customer_name,
                si.name AS invoice_no,
                si.posting_date AS posting_date,
                COALESCE(i.customs_tariff_number, '') AS customs_tariff_number,
                sii.item_name AS item_name,
                sii.qty AS total_qty,

                /* Row net before invoice-level discount */
                sii.base_net_amount AS row_net,

                /* Value Excl ST = row_net - (invoice_discount * share) */
                (sii.base_net_amount
                 - COALESCE(tx.inv_discount, 0) * COALESCE(sii.base_net_amount / NULLIF(tot.inv_net_total, 0), 0)
                ) AS base_net_amount,

                /* Sales Tax (row share of invoice GST) */
                (COALESCE(tx.inv_sales_tax, 0)
                 * COALESCE(sii.base_net_amount / NULLIF(tot.inv_net_total, 0), 0)
                ) AS sales_tax,

                /* Fixed Value = pure net (no ST, no discount) */
                sii.base_net_amount AS fixed_value

            FROM `tabSales Invoice` si
            JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
            LEFT JOIN `tabItem` i ON i.name = sii.item_code
            JOIN `tabCustomer` c ON c.name = si.customer
            LEFT JOIN ({taxes_subquery}) tx ON tx.invoice = si.name
            LEFT JOIN ({totals_subquery}) tot ON tot.invoice = si.name
            WHERE {condition_clause}
            ORDER BY si.posting_date DESC, si.name DESC, sii.idx
        """, filters, as_dict=True)

def cint_bool(v):
    return 1 if v in (True, 1, "1", "true", "True") else 0