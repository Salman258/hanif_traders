// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.query_reports["Warranty Ledger"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today()
    },
    {
      fieldname: "customer",
      label: __("Customer"),
      fieldtype: "Link",
      options: "Customer"
    },
    {
      fieldname: "item_code",
      label: __("Item Code"),
      fieldtype: "Link",
      options: "Item"
    },
    {
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      options: "Item Group"
    },
	{
      fieldname: "group_by_item",
      label: __("Group by Item"),
      fieldtype: "Check"
    }
  ]
};