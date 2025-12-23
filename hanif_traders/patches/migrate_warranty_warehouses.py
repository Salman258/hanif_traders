import frappe

def execute():
	"""
	Migrates custom warehouse fields to standard fields in Warranty DocType.
	"""
	# Reload DocType to ensure new fields exist in DB
	frappe.reload_doc("hanif_traders", "doctype", "warranty")

	# Check if custom columns exist before attempting migration
	if frappe.db.has_column("Warranty", "custom_default_receipt_warehouse"):
		frappe.db.sql("""
			UPDATE `tabWarranty`
			SET default_receipt_warehouse = custom_default_receipt_warehouse
			WHERE (default_receipt_warehouse IS NULL OR default_receipt_warehouse = '')
			AND custom_default_receipt_warehouse IS NOT NULL
		""")

	if frappe.db.has_column("Warranty", "custom_default_claim_warehouse"):
		frappe.db.sql("""
			UPDATE `tabWarranty`
			SET default_claim_warehouse = custom_default_claim_warehouse
			WHERE (default_claim_warehouse IS NULL OR default_claim_warehouse = '')
			AND custom_default_claim_warehouse IS NOT NULL
		""")
