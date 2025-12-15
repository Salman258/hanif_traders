// Copyright (c) 2025, Salman and contributors
// For license information, please see license.txt

frappe.ui.form.on("Warranty", {
    refresh(frm) {
        frm.trigger("set_item_query");
    },
    item_group(frm) {
        frm.trigger("set_item_query");
    },
    set_item_query(frm) {
        frm.set_query("item_code", "warranty_item_detail", function () {
            let filters = {};
            if (frm.doc.item_group) {
                filters.item_group = frm.doc.item_group;
            }
            return {
                filters: filters
            };
        });
    },
    validate(frm) {
        let total_received = 0;
        let total_claimed = 0;
        let total_balance = 0;
        let row_balance = 0;

        (frm.doc.warranty_item_detail || []).forEach(row => {
            // Calculate and update balance for each row
            row_balance = flt(row.quantity_received) - flt(row.quantity_claimed) - flt(row.replacement_quantity);
            frappe.model.set_value(row.doctype, row.name, "balance_quantity", row_balance);

            total_received += flt(row.quantity_received);
            total_claimed += flt(row.quantity_claimed) + flt(row.replacement_quantity);
            total_balance += row_balance;
        });

        frm.set_value('total_items_received', total_received);
        frm.set_value('total_items_claimed', total_claimed);
        frm.set_value('total_items_balanced', total_balance);

        frm.refresh_field("warranty_item_detail");
    }
});
