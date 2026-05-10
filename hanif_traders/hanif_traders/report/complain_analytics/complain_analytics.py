# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	
	return columns, data, None, chart, report_summary

def get_columns():
	return [
		{"label": _("Complain"), "fieldname": "name", "fieldtype": "Link", "options": "Complain", "width": 120},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
		{"label": _("Customer"), "fieldname": "complainer_name", "fieldtype": "Data", "width": 150},
		{"label": _("Phone"), "fieldname": "complainer_phone", "fieldtype": "Data", "width": 150},
		{"label": _("Territory"), "fieldname": "territory", "fieldtype": "Link", "options": "Territory", "width": 120},
		{"label": _("Technician"), "fieldname": "technician_name", "fieldtype": "Data", "width": 150},
		{"label": _("Status"), "fieldname": "workflow_state", "fieldtype": "Data", "width": 120},
		{"label": _("Resolution Date"), "fieldname": "resolution_date", "fieldtype": "Date", "width": 110},
		{"label": _("Time to Resolution (Hrs)"), "fieldname": "time_to_resolution", "fieldtype": "Float", "width": 145}
	]

def get_data(filters):
	conditions = get_conditions(filters)
	data = frappe.db.sql(f"""
		SELECT
			name, date, posting_time, complainer_name, complainer_phone, territory,
			technician_name, workflow_state, resolution_date, time_to_resolution
		FROM
			`tabComplain`
		WHERE
			docstatus < 2
			{conditions}
		ORDER BY
			date DESC, posting_time DESC
	""", filters, as_dict=1)

	# Calculate dynamic time for Open/Assigned complaints
	from frappe.utils import time_diff_in_hours, now_datetime, get_datetime

	for row in data:
		if row.workflow_state in ["Open", "Assigned"]:
			if row.date and row.get("posting_time"):
				start_time = get_datetime(f"{row.date} {row.get('posting_time', '00:00:00')}")
			else:
				start_time = get_datetime(row.date) if row.date else now_datetime()

			row.time_to_resolution = round(time_diff_in_hours(now_datetime(), start_time), 2)

	return data

def get_conditions(filters):
	conditions = ""
	date_field = filters.get("date_field") if filters.get("date_field") in ("date", "resolution_date") else "date"
	if filters.get("from_date") and filters.get("to_date"):
		conditions += f" AND {date_field} BETWEEN %(from_date)s AND %(to_date)s"
	if filters.get("technician"):
		conditions += " AND assigned_to_technician = %(technician)s"
	if filters.get("complainer_phone"):
		conditions += " AND complainer_phone LIKE %(complainer_phone)s"
	if filters.get("territory"):
		conditions += " AND territory = %(territory)s"
	if filters.get("workflow_state"):
		conditions += " AND workflow_state = %(workflow_state)s"
	return conditions

def get_chart(data):
	if not data:
		return None

	status_map = {}
	for row in data:
		status = row.get("workflow_state") or "Unknown"
		status_map[status] = status_map.get(status, 0) + 1

	labels = sorted(status_map.keys())
	values = [status_map[label] for label in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": "Complains", "values": values}]
		},
		"type": "donut",
		"height": 300
	}

def get_report_summary(data):
	if not data:
		return []

	total_complains = len(data)
	resolved_complains = 0
	total_time = 0.0
	resolved_count_for_avg = 0

	for row in data:
		if row.get("workflow_state") in ["Resolved", "CSC Verified"]:
			resolved_complains += 1
			val = row.get("time_to_resolution")
			if val:
				total_time += val
				resolved_count_for_avg += 1

	avg_time = total_time / resolved_count_for_avg if resolved_count_for_avg > 0 else 0

	return [
		{
			"value": total_complains,
			"indicator": "Blue",
			"label": _("Total Complains"),
			"datatype": "Int",
		},
		{
			"value": resolved_complains,
			"indicator": "Green",
			"label": _("Resolved"),
			"datatype": "Int",
		},
		{
			"value": f"{int(avg_time)}h {round((avg_time - int(avg_time)) * 60)}m",
			"indicator": "Orange",
			"label": _("Avg Resolution Time"),
			"datatype": "Data",
		}
	]
