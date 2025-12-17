# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.document import Document


class Warranty(Document):
	def validate(self):
		total_received = 0
		total_claimed = 0
		total_balance = 0

		for row in self.warranty_item_detail:
			
			# Calculate and update balance for each row
			row_balance = flt(row.quantity_received) - flt(row.quantity_claimed) - flt(row.replacement_quantity)
			row.balance_quantity = row_balance
			
			total_received += flt(row.quantity_received)
			total_claimed += flt(row.quantity_claimed) + flt(row.replacement_quantity)
			total_balance += row_balance

		self.total_items_received = total_received
		self.total_items_claimed = total_claimed
		self.total_items_balanced = total_balance

	def on_submit(self):
		from hanif_traders.api.warranty import create_stock_entry

		received_items = []
		claimed_items = []

		for row in self.warranty_item_detail:
			if row.quantity_received > 0:
				received_items.append({
					"item_code": row.item_code,
					"qty": row.quantity_received
				})

			if row.quantity_claimed > 0:
				claimed_items.append({
					"item_code": row.item_code,
					"qty": row.quantity_claimed
				})
				
				# Only add replacement item if it's specified and has quantity
				if row.replacement_item and row.replacement_quantity > 0:
					claimed_items.append({
						"item_code": row.replacement_item,
						"qty": row.replacement_quantity
					})
		
		# For Material Receipt -> use custom_default_receipt_warehouse mapped to 'to_warehouse'
		create_stock_entry(
			self,
			"Material Receipt",
			received_items,
			custom_warehouse_field="custom_default_receipt_warehouse",
			required_field_name="to_warehouse"
		)

		# For Material Issue -> use custom_default_claim_warehouse mapped to 'from_warehouse'
		create_stock_entry(
			self,
			"Material Issue",
			claimed_items,
			custom_warehouse_field="custom_default_claim_warehouse",
			required_field_name="from_warehouse"
		)
