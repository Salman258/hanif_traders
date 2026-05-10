import frappe


def execute():
	"""Convert time_to_resolution from Hours.Minutes encoding (1.30 = 1h 30m) to true decimal hours (1.5)."""
	rows = frappe.db.sql(
		"""
		SELECT name, time_to_resolution
		FROM `tabComplain`
		WHERE time_to_resolution IS NOT NULL AND time_to_resolution > 0
		""",
		as_dict=True,
	)

	for row in rows:
		old = float(row.time_to_resolution)
		hours = int(old)
		minutes = round((old - hours) * 100)
		new_value = round(hours + minutes / 60, 2)

		frappe.db.set_value(
			"Complain", row.name, "time_to_resolution", new_value, update_modified=False
		)

	frappe.db.commit()
