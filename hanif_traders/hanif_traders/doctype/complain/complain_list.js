frappe.listview_settings['Complain'] = {
    onload: function (listview) {
        listview.page.add_inner_button(__("Bulk Import Complains"), function () {
            frappe.set_route('data-import', 'new-data-import', 'Complain');
        }).addClass("btn-primary");
    },
    refresh: function (listview) {
        listview.page.add_inner_button(__("Bulk Assign"), function () {
            const selected_docs = listview.get_checked_items();
            const open_docs = selected_docs.filter(d => d.workflow_state === 'Open');

            if (open_docs.length === 0) {
                frappe.msgprint(__("Please select at least one 'Open' complaint to assign."));
                return;
            }

            if (open_docs.length < selected_docs.length) {
                frappe.msgprint(__("Only 'Open' complaints will be assigned. Others were ignored."));
            }

            const d = new frappe.ui.Dialog({
                title: __('Bulk Assign Complaints'),
                fields: [
                    {
                        label: 'Technician',
                        fieldname: 'technician',
                        fieldtype: 'Link',
                        options: 'Technician',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Assign'),
                primary_action(values) {
                    frappe.call({
                        method: 'hanif_traders.api.complain.bulk_assign',
                        args: {
                            complain_names: open_docs.map(d => d.name),
                            technician: values.technician
                        },
                        freeze: true,
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.msgprint(__("Complaints assigned successfully."));
                                listview.refresh();
                                d.hide();
                            }
                        }
                    });
                }
            });
            d.show();
        });
    }
};
