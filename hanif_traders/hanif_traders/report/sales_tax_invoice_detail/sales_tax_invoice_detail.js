/* Copyright (c) 2025, Salman and contributors */
/* For license information, please see license.txt */

/* global frappe */
frappe.query_reports["Sales Tax Invoice Detail"] = {
  filters: [
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      default: frappe.defaults.get_default("company")
    },
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      reqd: 1,
      // choose one: month_start() for full-month by default, or get_today() for today
      default: frappe.datetime.month_start(),
      change: () => {
        const fd = frappe.query_report.get_filter_value("from_date");
        const td = frappe.query_report.get_filter_value("to_date");
        if (fd && td && fd > td) {
          frappe.query_report.set_filter_value("to_date", fd);
        }
      }
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.month_end(),
      change: () => {
        const fd = frappe.query_report.get_filter_value("from_date");
        const td = frappe.query_report.get_filter_value("to_date");
        if (fd && td && fd > td) {
          frappe.query_report.set_filter_value("from_date", td);
        }
      }
    },

    // --- Optional convenience filters ---
    {
      fieldname: "customer",
      label: "Customer",
      fieldtype: "Link",
      options: "Customer"
    },
    {
      fieldname: "group_by_tariff",
      label: "Group by HS Code",
      fieldtype: "Check",
      default: 0
    }
  ]
};