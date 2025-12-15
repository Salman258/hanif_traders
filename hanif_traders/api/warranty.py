import frappe

def create_stock_entry(warranty_doc, purpose, items, custom_warehouse_field, required_field_name):
	if not items:
		return

	try:
		warehouse_value = warranty_doc.get(custom_warehouse_field)
		if not warehouse_value:
			label = custom_warehouse_field.replace("custom_", "").replace("_", " ").title()
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
				required_field_name: warehouse_value  # this must use standard ERPNext field
			})

		se.insert()
		se.submit()
		frappe.msgprint(f"✅ Stock Entry {se.name} created for {purpose}")

	except Exception as e:
		frappe.log_error(f"Stock Entry Creation Failed for {warranty_doc.name}", str(e))
		frappe.throw(f"Failed to create Stock Entry: {str(e)}")
