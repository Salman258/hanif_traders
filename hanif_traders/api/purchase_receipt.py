import frappe

def explode_bundle_items(doc, method):
	# Clear previous packed items
	doc.custom_packed_items = []

	for item in doc.items:
		# Check if item is a Product Bundle
		product_bundle = frappe.get_all("Product Bundle", filters={"new_item_code": item.item_code}, limit=1)
		
		if not product_bundle:
			continue

		bundle_name = product_bundle[0].name
		bundle_items = frappe.get_all("Product Bundle Item",
									  filters={"parent": bundle_name},
									  fields=["item_code", "description", "qty"])

		for bundle_item in bundle_items:
			doc.append("custom_packed_items", {
				"parent_item": item.item_code,
				"item_code": bundle_item.item_code,
				"item_name": bundle_item.description,
				"description": bundle_item.description,
				"qty": bundle_item.qty * item.qty,
				"base_rate": 0,
				"uom": item.uom,
				"target_warehouse": doc.set_warehouse
			})

def create_stock_entry_on_submit(doc, method):
	if doc.custom_packed_items:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Receipt"
		stock_entry.custom_purchase_receipt = doc.name
		stock_entry.company = doc.company
		stock_entry.posting_date = doc.posting_date
		stock_entry.posting_time = doc.posting_time
		stock_entry.set_posting_time = 1

		for item in doc.custom_packed_items:
			stock_entry.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"uom": item.uom,
				"stock_uom": item.uom,
				"rate": item.base_rate,
				"conversion_factor": 1,
				"t_warehouse": item.target_warehouse,
				"allow_zero_valuation_rate": True
			})

		stock_entry.save()
		stock_entry.submit()
		frappe.msgprint(f"✅ Stock Entry {stock_entry.name} created for Packed Items")

def cancel_stock_entry(doc, method):
	stock_entries = frappe.get_all("Stock Entry", filters={"custom_purchase_receipt": doc.name, "docstatus": 1})
	for se in stock_entries:
		se_doc = frappe.get_doc("Stock Entry", se.name)
		se_doc.cancel()
		frappe.msgprint(f"✅ Stock Entry {se.name} cancelled")
