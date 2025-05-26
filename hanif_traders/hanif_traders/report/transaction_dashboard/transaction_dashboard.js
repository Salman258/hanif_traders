// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.query_reports["Transaction Dashboard"] = {

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "status") {
            if (value === "Pending") {
                value = `<span style="background-color: #fff3cd; padding: 2px 4px;">${value}</span>`;
            } else if (value === "Posted") {
                value = `<span style="background-color: #d1ecf1; padding: 2px 4px;">${value}</span>`;
            } else if (value === "Returned") {
                value = `<span style="background-color: #f8d7da; padding: 2px 4px;">${value}</span>`;
            }else if (value === "In Clearing") {
                value = `<span style="background-color: #fff3cd; padding: 2px 4px;">${value}</span>`;
            }
        }
        return value;
    },
    "filters": [
        {
            fieldname: "party_type",
            label: "Party Type",
            fieldtype: "Link",
            options:"Party Type",
            reqd: 0
        },
        {
            fieldname: "party",
            label: "Party",
            fieldtype: "Dynamic Link",
            options: "party_type",
            reqd: 0
        },
        {
            fieldname: "account",
            label: "Account",
            fieldtype: "Link",
            options: "Account",
            reqd: 0
        },
        {
            fieldname: "status",
            label: "Status",
            fieldtype: "Select",
            options: [
                "",
                "Pending",
                "Posted",
                "In Clearing",
                "Canceled",
                "Returned"
            ],
            reqd: 0
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        }
    ]
};
