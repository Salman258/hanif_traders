# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, add_months, flt
from datetime import datetime, timedelta
import statistics


def execute(filters=None):
	"""Main entry point for the report"""
	if not filters:
		filters = {}
	
	# Validate required filter
	if not filters.get("customer"):
		frappe.throw(_("Please select a Customer"))
	
	# Set default dates if not provided
	if not filters.get("from_date"):
		filters["from_date"] = get_fiscal_year_start(filters.get("to_date") or frappe.utils.today())
	if not filters.get("to_date"):
		filters["to_date"] = frappe.utils.today()
	
	columns = get_columns()
	data = get_data(filters)
	chart = None
	report_summary = get_report_summary(filters, data)
	
	return columns, data, None, chart, report_summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "balance",
			"label": _("Balance"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150
		},
		{
			"fieldname": "against",
			"label": _("Against Account"),
			"fieldtype": "Data",
			"width": 150
		}
	]


def get_data(filters):
	"""Fetch GL entries for the customer"""
	customer = filters.get("customer")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	
	# Get opening balance (before from_date)
	opening_balance = frappe.db.sql("""
		SELECT SUM(debit - credit) as balance
		FROM `tabGL Entry`
		WHERE party_type = 'Customer'
			AND party = %(customer)s
			AND posting_date < %(from_date)s
			AND is_cancelled = 0
			AND docstatus = 1
	""", {
		"customer": customer,
		"from_date": from_date
	})[0][0] or 0
	
	gl_entries = frappe.db.sql("""
		SELECT
			posting_date,
			remarks,
			debit,
			credit,
			voucher_type,
			voucher_no,
			against
		FROM `tabGL Entry`
		WHERE party_type = 'Customer'
			AND party = %(customer)s
			AND posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND is_cancelled = 0
			AND docstatus = 1
		ORDER BY posting_date ASC, creation ASC
	""", {
		"customer": customer,
		"from_date": from_date,
		"to_date": to_date
	}, as_dict=1)
	
	# Calculate running balance
	running_balance = opening_balance
	for entry in gl_entries:
		running_balance += (entry.debit or 0) - (entry.credit or 0)
		entry['balance'] = running_balance
	
	return gl_entries


def get_report_summary(filters, data):
	"""Calculate all credit circulation metrics and return as report summary"""
	customer = filters.get("customer")
	report_date = getdate(filters.get("to_date"))
	fy_start = get_fiscal_year_start(report_date)
	
	# Calculate all metrics
	metrics = calculate_credit_metrics(customer, fy_start, report_date)
	frappe.msgprint(get_indicator_color(metrics["rating"]))
	
	# Build report summary
	summary = []
	
	# Primary Metrics - First Row
	summary.append({
		"value": metrics["ccr"],
		"indicator": get_indicator_color(metrics["rating"]),
		"label": _("Credit Circulation Rating (CCR)"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["rating"],
		"indicator": get_indicator_color(metrics["rating"]),
		"label": _("Rating"),
		"datatype": "Data"
	})
	
	summary.append({
		"value": metrics["action"],
		"indicator": get_indicator_color(metrics["rating"]),
		"label": _("Recommended Action"),
		"datatype": "Data"
	})
	
	summary.append({
		"value": metrics["circulation_weeks"],
		"label": _("Circulation Period (Weeks)"),
		"datatype": "Float"
	})
	
	# Component Scores - Second Row
	summary.append({
		"value": metrics["ccw_score"],
		"label": _("Credit Circulation Score (40%)"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["cur_score"],
		"label": _("Credit Utilization Score (15%)"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["scm_score"],
		"label": _("Sales-Credit Multiple Score (15%)"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["ovi_score"],
		"label": _("Volatility Score (10%)"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["bli_score"],
		"label": _("Longevity Score (10%)"),
		"datatype": "Float"
	})
	
	# Supporting Data - Third Row
	summary.append({
		"value": metrics["total_payments"],
		"label": _("Total Payments (FY)"),
		"datatype": "Currency"
	})
	
	summary.append({
		"value": metrics["avg_outstanding"],
		"label": _("Avg Outstanding"),
		"datatype": "Currency"
	})
	
	summary.append({
		"value": metrics["annualized_payments"],
		"label": _("Annualized Payments"),
		"datatype": "Currency"
	})
	
	summary.append({
		"value": metrics["ctr"],
		"label": _("Credit Turnover Ratio"),
		"datatype": "Float"
	})
	
	summary.append({
		"value": metrics["total_sales"],
		"label": _("Total Sales (FY)"),
		"datatype": "Currency"
	})
	
	summary.append({
		"value": metrics["credit_limit"],
		"label": _("Credit Limit"),
		"datatype": "Currency"
	})
	
	summary.append({
		"value": metrics["years_active"],
		"label": _("Years Active"),
		"datatype": "Float"
	})
	
	return summary


def calculate_credit_metrics(customer, fy_start, report_date):
	"""Calculate all credit circulation metrics"""
	
	# 1. Calculate weeks elapsed
	weeks_elapsed = (report_date - fy_start).days / 7.0
	
	# 2. Total Payments (FY-to-date)
	total_payments = frappe.db.sql("""
		SELECT SUM(credit) as total
		FROM `tabGL Entry`
		WHERE party_type = 'Customer'
			AND party = %s
			AND posting_date BETWEEN %s AND %s
			AND is_cancelled = 0
			AND docstatus = 1
	""", (customer, fy_start, report_date))[0][0] or 0
	
	# 3. Average Outstanding Exposure (monthly closing balances)
	monthly_balances = get_monthly_closing_balances(customer, fy_start, report_date)
	avg_outstanding = statistics.mean(monthly_balances) if monthly_balances else 0
	
	# 4. Annualize Payments (52-week basis)
	if weeks_elapsed > 0:
		annualized_payments = total_payments * (52 / weeks_elapsed)
	else:
		annualized_payments = 0
	
	# 5. Credit Turnover Ratio
	if avg_outstanding > 0:
		ctr = annualized_payments / avg_outstanding
	else:
		ctr = float('inf')
	
	# 6. Circulation Period (weeks)
	if ctr > 0 and ctr != float('inf'):
		circulation_weeks = 52 / ctr
	else:
		circulation_weeks = float('inf')
	
	# 7. Credit Circulation Score
	if circulation_weeks <= 4:
		ccw_score = 100
	elif circulation_weeks <= 6:
		ccw_score = 85
	elif circulation_weeks <= 9:
		ccw_score = 70
	elif circulation_weeks <= 12:
		ccw_score = 50
	else:
		ccw_score = 30
	
	# 8. Credit Utilization Ratio and Score
	# Note: ERPNext uses credit_limits child table, not a direct field
	# For simplicity, we'll check if customer has any credit limits set
	try:
		credit_limits = frappe.db.sql("""
			SELECT credit_limit
			FROM `tabCustomer Credit Limit`
			WHERE parent = %s
			ORDER BY credit_limit DESC
			LIMIT 1
		""", (customer,))
		credit_limit = credit_limits[0][0] if credit_limits else 0
	except Exception:
		# Fallback if credit limits table doesn't exist or has issues
		credit_limit = 0
	
	if credit_limit > 0:
		utilization_ratio = avg_outstanding / credit_limit
	else:
		utilization_ratio = 0
	
	if 0.6 <= utilization_ratio <= 0.85:
		cur_score = 100
	elif 0.4 <= utilization_ratio < 0.6 or 0.85 < utilization_ratio <= 0.95:
		cur_score = 75
	else:
		cur_score = 50
	
	# 9. Sales-to-Credit Multiple
	total_sales = frappe.db.sql("""
		SELECT SUM(grand_total) as total
		FROM `tabSales Invoice`
		WHERE customer = %s
			AND posting_date BETWEEN %s AND %s
			AND docstatus = 1
	""", (customer, fy_start, report_date))[0][0] or 0
	
	if avg_outstanding > 0:
		sales_credit_multiple = total_sales / avg_outstanding
	else:
		sales_credit_multiple = float('inf')
	
	if sales_credit_multiple >= 12:
		scm_score = 100
	elif sales_credit_multiple >= 8:
		scm_score = 85
	elif sales_credit_multiple >= 5:
		scm_score = 70
	else:
		scm_score = 40
	
	# 10. Outstanding Volatility Index
	if avg_outstanding > 0 and len(monthly_balances) > 1:
		volatility_index = statistics.stdev(monthly_balances) / avg_outstanding
	else:
		volatility_index = 0
	
	if volatility_index < 0.3:
		ovi_score = 100
	elif volatility_index <= 0.6:
		ovi_score = 70
	else:
		ovi_score = 40
	
	# 11. Business Longevity Index
	first_invoice_date = frappe.db.sql("""
		SELECT MIN(posting_date)
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 1
	""", (customer,))[0][0]
	
	if first_invoice_date:
		years_active = (report_date - first_invoice_date).days / 365.25
	else:
		years_active = 0
	
	bli_score = min(100, (years_active / 3) * 100)
	
	# 12. Final CCR (weighted composite)
	ccr = (
		0.40 * ccw_score +
		0.15 * cur_score +
		0.15 * scm_score +
		0.10 * ovi_score +
		0.10 * bli_score
	)
	
	# 13. Rating and Action
	if ccr >= 85:
		rating = "Elite"
		action = "Increase Credit"
	elif ccr >= 70:
		rating = "Strong"
		action = "Maintain"
	elif ccr >= 55:
		rating = "Stable"
		action = "Monitor"
	elif ccr >= 40:
		rating = "Slow"
		action = "Recover Payment"
	else:
		rating = "Risk"
		action = "Restrict"
	
	# Return all metrics
	return {
		"total_payments": flt(total_payments, 2),
		"avg_outstanding": flt(avg_outstanding, 2),
		"annualized_payments": flt(annualized_payments, 2),
		"ctr": flt(ctr, 2) if ctr != float('inf') else 0,
		"circulation_weeks": flt(circulation_weeks, 2) if circulation_weeks != float('inf') else 0,
		"ccw_score": flt(ccw_score, 2),
		"cur_score": flt(cur_score, 2),
		"scm_score": flt(scm_score, 2),
		"ovi_score": flt(ovi_score, 2),
		"bli_score": flt(bli_score, 2),
		"ccr": flt(ccr, 2),
		"rating": rating,
		"action": action,
		"total_sales": flt(total_sales, 2),
		"credit_limit": flt(credit_limit, 2),
		"years_active": flt(years_active, 2)
	}


def get_monthly_closing_balances(customer, fy_start, report_date):
	"""Get closing balance for each month in the fiscal year to date"""
	balances = []
	current_date = get_last_day(fy_start)
	end_date = get_last_day(report_date)
	
	while current_date <= end_date:
		balance = get_customer_closing_balance(customer, current_date)
		balances.append(balance)
		current_date = get_last_day(add_months(current_date, 1))
	
	return balances


def get_customer_closing_balance(customer, as_on_date):
	"""Get customer's closing balance as on a specific date"""
	balance = frappe.db.sql("""
		SELECT SUM(debit - credit) as balance
		FROM `tabGL Entry`
		WHERE party_type = 'Customer'
			AND party = %s
			AND posting_date <= %s
			AND is_cancelled = 0
			AND docstatus = 1
	""", (customer, as_on_date))[0][0] or 0
	
	return flt(balance, 2)


def get_fiscal_year_start(date):
	"""Get fiscal year start date for a given date"""
	fiscal_year = frappe.db.sql("""
		SELECT year_start_date
		FROM `tabFiscal Year`
		WHERE %s BETWEEN year_start_date AND year_end_date
		LIMIT 1
	""", (date,))
	
	if fiscal_year:
		return fiscal_year[0][0]
	else:
		# Default to current year October 1st if no fiscal year found
		year = getdate(date).year
		return getdate(f"{year}-10-01")


def get_indicator_color(rating):
	"""Return indicator color based on rating"""
	# ERPNext supported colors: Green, Blue, Orange, Red, Purple, Light Blue, Gray
	# Yellow is NOT supported
	color_map = {
		"Elite": "Green",
		"Strong": "Blue",
		"Stable": "Orange",
		"Slow": "Blue",  # Changed from Yellow (not supported)
		"Risk": "Red"
	}
	return color_map.get(rating, "Gray")
