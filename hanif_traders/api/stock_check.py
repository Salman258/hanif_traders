import frappe
from frappe import _

@frappe.whitelist()
def get_stock_balance(item_code=None, item_group=None, warehouse=None):
    results = []

    def add_bin_results(item_doc, wh_filter=None):
        bin_filters = {"item_code": item_doc.name}
        if wh_filter:
            bin_filters["warehouse"] = wh_filter

        bins = frappe.get_all("Bin", filters=bin_filters, fields=["warehouse", "actual_qty"])
        for b in bins:
            results.append({
                "item_code": item_doc.name,
                "item_name": item_doc.item_name,
                "description": item_doc.description,
                "item_group": item_doc.item_group,
                "warehouse": b.warehouse,
                "actual_qty": b.actual_qty,
                "is_stock_item": item_doc.is_stock_item
            })

    if item_code:
        item = frappe.get_doc("Item", item_code)
        if not item.is_stock_item:
            # It's a non-stock item → check product bundle children
            bundles = frappe.get_all("Product Bundle", filters={"new_item_code": item_code})
            for bundle in bundles:
                children = frappe.get_all("Product Bundle Item", filters={"parent": bundle.name}, fields=["item_code"])
                for child in children:
                    child_doc = frappe.get_doc("Item", child.item_code)
                    # Apply item_group filter to child items if provided
                    if item_group and child_doc.item_group != item_group:
                        continue
                    add_bin_results(child_doc, warehouse)
        else:
            if item_group and item.item_group != item_group:
                return []
            add_bin_results(item, warehouse)

    elif item_group or warehouse:
        item_filters = {"is_stock_item": 1}
        if item_group:
            item_filters["item_group"] = item_group

        items = frappe.get_all("Item", filters=item_filters, fields=["name"])
        for i in items:
            item_doc = frappe.get_doc("Item", i.name)
            add_bin_results(item_doc, warehouse)

    return results
