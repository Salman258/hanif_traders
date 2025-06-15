// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Tax Invoice Detail"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": "Today",
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": "Today",
			"reqd": 1
		},
		{
			"fieldname": "group_by_tariff",
			"label": "Group by HS Code",
			"fieldtype": "Check",
			"default": 0
		}

	]
};
