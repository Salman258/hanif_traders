frappe.query_reports["Transaction Dashboard"] = {
    formatter: function(value, row, column, data, default_formatter) {
        formatted = default_formatter(value, row, column, data);
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
        try{
            if (column.fieldname === "quick_view") {
                formatted = `<button class="btn btn-sm btn-primary quick-view-btn" data-entry="${data.name}" style="padding: 6px 12px; font-size: 13px;">🔍 View</button>`;
            }
        }catch(err){
	        console.log('Error throwing because of last column its -> Total Row')
	        console.log(err)
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
            fieldname: "account",
            label: "Account",
            fieldtype: "Link",
            options: "Account"
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

    after_datatable_render: function (datatable) {
        const wrapper = datatable.wrapper;

        // Prevent multiple bindings
        if (wrapper.quick_view_listener_attached) return;
        wrapper.quick_view_listener_attached = true;

        wrapper.addEventListener('click', function (e) {
            if (e.target && e.target.classList.contains('quick-view-btn')) {
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
                    callback: function (r) {
                        if (!r.exc && r.message) {
                         const je = r.message;

                        // Build HTML for Journal Entry Account table
                        let account_rows = (je.accounts || []).map(acc => `
                            <tr>
                                <td>${acc.account}</td>
                                <td>${acc.party || ''}</td>
                                <td>${acc.party_name || ''}</td>
                                <td style="text-align: right;">${acc.debit || 0}</td>
                                <td style="text-align: right;">${acc.credit || 0}</td>
                                <td>${acc.user_remark || ''}</td>
                            </tr>
                        `).join('');

                        let account_table_html = `
                            <table class="table table-bordered table-sm">
                                <thead>
                                    <tr>
                                        <th>Account</th>
                                        <th>Party</th>
                                        <th>Party Name</th>
                                        <th>Debit</th>
                                        <th>Credit</th>
                                        <th>Remark</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${account_rows}
                                </tbody>
                            </table>
                        `;

                        const d = new frappe.ui.Dialog({
                            title: `Journal Entry: ${je.name}`,
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
                                    fieldname: "account_table",
                                    options: account_table_html
                                }
                            ],
                            size: "large",
                            primary_action_label: "Close",
                            primary_action() {
                                d.hide();
                            }
                        });
                        d.show();
                        }
                    }
                });
            }
        });
    },

    
};

