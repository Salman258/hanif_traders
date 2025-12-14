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
		{"label": _("Rank"), "fieldname": "rank", "fieldtype": "Int", "width": 50},
		{"label": _("Technician"), "fieldname": "technician", "fieldtype": "Link", "options": "Technician", "width": 180},
		{"label": _("Technician Name"), "fieldname": "technician_name", "fieldtype": "Data", "width": 180},
		{"label": _("Total Points"), "fieldname": "total_points", "fieldtype": "Int", "width": 120},
		{"label": _("Complaints Resolved"), "fieldname": "complaints_resolved", "fieldtype": "Int", "width": 150}
	]

def get_data(filters):
	# Auto-calculate dates: 1st of current month to Today
	today_date = frappe.utils.today()
	from_date = frappe.utils.get_first_day(today_date)
	to_date = today_date

	# 1. Get Points per Technician
	points_data = frappe.db.sql("""
		SELECT technician, SUM(points) as total_points
		FROM `tabTechnician Points Log`
		WHERE posting_date BETWEEN %s AND %s
		GROUP BY technician
	""", (from_date, to_date), as_dict=1)
	
	points_map = {d.technician: d.total_points for d in points_data}

	# 2. Get Resolved Complaints count per Technician
	complaints_data = frappe.db.sql("""
		SELECT assigned_to_technician as technician, COUNT(name) as count
		FROM `tabComplain`
		WHERE 
			workflow_state IN ('Resolved', 'CSC Verified')
			AND resolution_date BETWEEN %s AND %s
		GROUP BY assigned_to_technician
	""", (from_date, to_date), as_dict=1)

	complaints_map = {d.technician: d.count for d in complaints_data}

	# 3. Get all Technicians to ensure we show even those with 0 points if needed, 
	# but for leaderboard, usually only active ones. Let's fetch all active technicians.
	technicians = frappe.get_all("Technician", fields=["name", "technician_name"])

	result = []
	for tech in technicians:
		pts = points_map.get(tech.name, 0)
		resolved = complaints_map.get(tech.name, 0)
		
		if pts > 0 or resolved > 0:
			result.append({
				"technician": tech.name,
				"technician_name": tech.technician_name,
				"total_points": pts,
				"complaints_resolved": resolved
			})

	# 4. Sort by Total Points DESC
	result.sort(key=lambda x: x["total_points"], reverse=True)

	# 5. Add Rank
	for idx, row in enumerate(result):
		row["rank"] = idx + 1

	return result

def get_chart(data):
	if not data:
		return None

	# Top 10
	top_data = data[:10]
	labels = [d["technician_name"] for d in top_data]
	values = [d["total_points"] for d in top_data]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": "Total Points", "values": values}]
		},
		"type": "bar",
		"height": 300
	}

def get_report_summary(data):
	if not data:
		return []

	top_tech = data[0] if data else None
	total_points = sum(d["total_points"] for d in data)
	total_resolved = sum(d["complaints_resolved"] for d in data)

	summary = []

	if top_tech:
		summary.append({
			"value": f"{top_tech['technician_name']} ({top_tech['total_points']} pts)",
			"indicator": "Gold",
			"label": _("Top Technician"),
			"datatype": "Data",
		})
	else:
		summary.append({
			"value": "N/A",
			"indicator": "Grey",
			"label": _("Top Technician"),
			"datatype": "Data",
		})

	summary.append({
		"value": total_points,
		"indicator": "Blue",
		"label": _("Total Points Awarded"),
		"datatype": "Int",
	})

	summary.append({
		"value": total_resolved,
		"indicator": "Green",
		"label": _("Complaints Resolved"),
		"datatype": "Int",
	})

	return summary
