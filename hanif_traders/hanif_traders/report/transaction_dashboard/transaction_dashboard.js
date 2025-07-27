frappe.query_reports["Transaction Dashboard"] = {
    formatter: function(value, row, column, data, default_formatter) {
        let formatted = default_formatter(value, row, column, data);

        if (column.fieldname === "status") {
            if (value === "Pending") {
                formatted = `<span style="background-color: #fff3cd; padding: 2px 4px;">${value}</span>`;
            } else if (value === "Posted") {
                formatted = `<span style="background-color: #d1ecf1; padding: 2px 4px;">${value}</span>`;
            } else if (value === "Returned") {
                formatted = `<span style="background-color: #f8d7da; padding: 2px 4px;">${value}</span>`;
            } else if (value === "In Clearing") {
                formatted = `<span style="background-color: #fff3cd; padding: 2px 4px;">${value}</span>`;
            }
        }

        try {
            if (column.fieldname === "quick_view") {
                formatted = `<button class="btn btn-sm btn-primary quick-view-btn" data-entry="${data.name}" style="padding: 6px 12px; font-size: 13px;">🔍 View</button>`;
            }
        } catch (err) {
            console.log("Error in last column (probably total row)", err);
        }

        return formatted;
    },

    filters: [
        {
            fieldname: "party_type",
            label: "Party Type",
            fieldtype: "Link",
            options: "Party Type"
        },
        {
            fieldname: "party",
            label: "Party",
            fieldtype: "Dynamic Link",
            options: "party_type"
        },
        {
            "fieldname": "credit_account",
            "label": __("Credit Account"),
            "fieldtype": "Link",
            "options": "Account"
        },
        {
            "fieldname": "debit_account",
            "label": __("Debit Account"),
            "fieldtype": "Link",
            "options": "Account"
        },
        {
            fieldname: "status",
            label: "Status",
            fieldtype: "Select",
            options: ["", "Pending", "Posted", "In Clearing", "Canceled", "Returned"]
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
    ],

    after_datatable_render: function(datatable) {
        const wrapper = datatable.wrapper;

        // Prevent multiple bindings
        if (wrapper.quick_view_listener_attached) return;
        wrapper.quick_view_listener_attached = true;

        wrapper.addEventListener("click", function(e) {
            if (e.target && e.target.classList.contains("quick-view-btn")) {
                const entry_name = e.target.getAttribute("data-entry");

                if (!entry_name) {
                    frappe.msgprint("Entry not found.");
                    return;
                }

                frappe.call({
                    method: "frappe.client.get",
                    args: {
                        doctype: "Journal Entry",
                        name: entry_name
                    },
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            const je = r.message;

                            const d = new frappe.ui.Dialog({
                                title: `Journal Entry: <a href="/app/journal-entry/${je.name}" target="_blank">${je.name}</a>`,
                                fields: [
                                    {
                                        label: "Posting Date",
                                        fieldtype: "Date",
                                        default: je.posting_date,
                                        read_only: 1
                                    },
                                    {
                                        label: "Status",
                                        fieldtype: "Data",
                                        default: je.workflow_state || je.docstatus,
                                        read_only: 1
                                    },
                                    {
                                        label: "Reference No",
                                        fieldtype: "Data",
                                        default: je.cheque_no,
                                        read_only: 1
                                    },
                                    {
                                        label: "Remarks",
                                        fieldtype: "Small Text",
                                        default: je.remark,
                                        read_only: 1
                                    },
                                    {
                                        fieldtype: "HTML",
                                        fieldname: "account_table"
                                    }
                                ],
                                size: "large",
                                primary_action_label: "Close",
                                primary_action() {
                                    d.hide();
                                }
                            });

                            d.show();

                            setTimeout(() => {
                                const container = d.fields_dict.account_table.$wrapper.get(0);
                                container.innerHTML = "";

                                const account_data = (je.accounts || []).map(row => ({
                                    'Account': row.account,
                                    'Party': row.party || "",
                                    'Party Name': row.party_name || "",
                                    'Debit': row.debit || 0,
                                    'Credit': row.credit || 0,
                                    'Remark': row.user_remark || ""
                                }));

                                const datatable = new frappe.DataTable(container, {
                                    columns: [
                                        { name: "Account", width: 150 },
                                        { name: "Party", width: 150 },
                                        { name: "Party Name", width: 200 },
                                        { name: "Debit", align: "right", width: 150, format: (value, row) => frappe.format(value, { fieldtype: "Currency" }, null, row) },
                                        { name: "Credit", align: "right", width: 150, format: (value, row) => frappe.format(value, { fieldtype: "Currency" }, null, row) },
                                        { name: "Remark", width: 100 }
                                    ],
                                    data: account_data,
                                    layout: "fixed",
                                    noDataMessage: "No account entries found.",
                                    inlineFilters: true,
                                    enableSorting: true
                                });
                                d.$wrapper.on('hide.bs.modal', () => {
                                datatable.destroy();
                                });    
                            }, 300);
                        }
                    }
                });
            }
        });
    }
};
