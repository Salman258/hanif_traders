import frappe

def execute():
	"""
	Migrates custom reference fields to standard fields in Warranty DocType.
	"""
	# Reload DocType to ensure new fields exist in DB
	frappe.reload_doc("hanif_traders", "doctype", "warranty")

	# Map: New Field -> Old Custom Field
	field_map = {
		"book_reference_no": "custom_book_reference_no",
		"receiver_name": "custom_receiver_name",
		"receiver_contact": "custom_receiver_contact"
	}

	for new_field, old_field in field_map.items():
		if frappe.db.has_column("Warranty", old_field):
			frappe.db.sql(f"""
				UPDATE `tabWarranty`
				SET {new_field} = {old_field}
				WHERE ({new_field} IS NULL OR {new_field} = '')
				AND {old_field} IS NOT NULL
			""")
