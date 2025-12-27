import frappe
from frappe.utils import flt

def create_stock_entry(warranty_doc, purpose, items, warehouse_field, required_field_name):
	if not items:
		return

	try:
		warehouse_value = warranty_doc.get(warehouse_field)
		if not warehouse_value:
			label = warehouse_field.replace("_", " ").title()
			frappe.throw(f"Please set '{label}' in the Warranty document.")

		se = frappe.new_doc("Stock Entry")
		se.purpose = purpose
		se.stock_entry_type = purpose
		se.custom_warranty = warranty_doc.name
		se.set(required_field_name, warehouse_value)  # set warehouse at header level

		for item in items:
			se.append("items", {
				"item_code": item["item_code"],
				"qty": item["qty"],
				"uom": frappe.db.get_value("Item", item["item_code"], "stock_uom"),
				"conversion_factor": 1,
				"allow_zero_valuation_rate": 1,
				required_field_name: warehouse_value
			})

		se.insert()
		se.submit()
		#frappe.msgprint(f"✅ Stock Entry {se.name} created for {purpose}")

	except Exception as e:
		frappe.log_error(f"Stock Entry Creation Failed for {warranty_doc.name}", str(e))
		frappe.throw(f"Failed to create Stock Entry: {str(e)}")

def create_journal_entry(warranty_doc, claimed_items):
	if not claimed_items:
		return

	total_amount = 0
	for row in warranty_doc.warranty_item_detail:
		if row.quantity_claimed > 0:
			total_amount += flt(row.quantity_claimed) * flt(row.rate)

	if total_amount == 0:
		return

	company = frappe.defaults.get_user_default("Company")
	if not company:
		frappe.throw("Please set a default Company in Global Defaults or User Defaults.")

	expense_account = frappe.db.get_value("Account", {"account_number": "1450", "company": company}, "name")
	if not expense_account:
		expense_account = frappe.db.get_value("Account", {"account_name": ["like", "%Warranty Sale Return%"], "company": company}, "name")
	
	if not expense_account:
		frappe.throw(f"Could not find Expense Account '1450 - Customer Warranty Sale Return' for company {company}.")

	customer_account = frappe.db.get_value("Account", {"account_number": "1310", "company": company}, "name")
	if not customer_account:
		frappe.throw(f"Could not determine Debtor Account for company {company}.")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Credit Note"
	je.company = company
	je.posting_date = warranty_doc.date
	je.remark = f"Credit Note for Warranty {warranty_doc.name}"

	je.append("accounts", {
		"account": expense_account,
		"debit_in_account_currency": total_amount,
		"cost_center": frappe.get_value("Company", company, "cost_center")
	})

	je.append("accounts", {
		"account": customer_account,
		"credit_in_account_currency": total_amount,
		"party_type": "Customer",
		"party": warranty_doc.customer
	})

	je.save()
	#je.submit()
	
	warranty_doc.db_set("journal_entry", je.name)
	frappe.msgprint(f"✅ Journal Entry {je.name} created for Credit Note")



