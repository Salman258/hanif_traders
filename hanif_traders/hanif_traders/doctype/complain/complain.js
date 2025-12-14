// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.ui.form.on('Complain', {
    refresh(frm) {
        // Dynamic Time to Resolution
        if (['Open', 'Assigned'].includes(frm.doc.workflow_state) && frm.doc.date && frm.doc.posting_time) {
            const start_str = frm.doc.date + " " + frm.doc.posting_time;
            const start_time = frappe.datetime.str_to_obj(start_str);
            const now = new Date();
            const diff_ms = now - start_time;
            const total_hours = diff_ms / (1000 * 60 * 60);
            const hours = Math.floor(total_hours);
            const minutes = (total_hours - hours) * 60;
            const formatted_time = hours + (minutes / 100);

            // Update directly to avoid 'unsaved changes' (dirty) state
            frm.doc.time_to_resolution = parseFloat(formatted_time.toFixed(2));
            frm.refresh_field('time_to_resolution');
        }

        if (frm.doc.workflow_state === 'Assigned' && frm.doc.complain_csc) {
            frm.add_custom_button('🔐 Verify CSC', () => {
                const d = new frappe.ui.Dialog({
                    title: 'Verify CSC Code',
                    fields: [{
                        fieldtype: 'Data',
                        fieldname: 'csc_input',
                        label: '4-digit Code',
                        reqd: 1
                    }],
                    primary_action(values) {
                        d.hide();
                        frappe.call({
                            method: 'hanif_traders.api.complain.verify_csc',
                            args: {
                                complain_name: frm.doc.name,
                                input_code: values.csc_input
                            },
                            callback: r => {
                                if (r.exc) {
                                    frappe.msgprint(`❌ ${r.exc}`);
                                } else {
                                    frappe.msgprint(`✅ ${r.message}`);
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });
                d.show();
            });
        }
    }
});
