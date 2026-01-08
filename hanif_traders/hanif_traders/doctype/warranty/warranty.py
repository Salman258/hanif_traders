# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt
import frappe
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_item_details

class Warranty(Document):
	def validate(self):
		self.set_pricing_details()
		self.validate_balances()
		self.validate_warranty_type()

	def before_save(self):
		if self.claim_settlement_type == "Credit Note":
			self.credit_note_details = self.get_credit_note_details_html()
		else:
			self.credit_note_details = None
	
	def on_submit(self):
		if self.claim_settlement_type == "Credit Note":
			self.create_credit_entries()
		else:
			self.create_replacement_entries()

	def validate_balances(self):
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

	def validate_warranty_type(self):
		if self.claim_settlement_type == "Credit Note":
			for row in self.warranty_item_detail:
				if row.quantity_claimed > 0 and flt(row.rate) <= 0:
					frappe.throw(f"Row #{row.idx}: Rate cannot be zero when Claim Settlement Type is 'Credit Note' and Quantity Claimed is greater than zero.")

	def get_received_items(self):
		received_items = []
		for row in self.warranty_item_detail:
			if row.quantity_received > 0:
				received_items.append({
					"item_code": row.item_code,
					"qty": row.quantity_received
				})
		return received_items

	def get_claimed_items(self):
		claimed_items = []
		for row in self.warranty_item_detail:
			if row.quantity_claimed > 0:
				claimed_items.append({
					"item_code": row.item_code,
					"qty": row.quantity_claimed
				})
				if row.replacement_item and row.replacement_quantity > 0:
					claimed_items.append({
						"item_code": row.replacement_item,
						"qty": row.replacement_quantity
					})
		return claimed_items

	def create_stock_entry(self, purpose, items, warehouse_field, required_field_name):
		if not items:
			return

		try:
			warehouse_value = self.get(warehouse_field)
			if not warehouse_value:
				label = warehouse_field.replace("_", " ").title()
				frappe.throw(f"Please set '{label}' in the Warranty document.")

			se = frappe.new_doc("Stock Entry")
			se.purpose = purpose
			se.stock_entry_type = purpose
			se.custom_warranty = self.name
			se.set(required_field_name, warehouse_value)

			for item in items:
				se.append("items", {
					"item_code": item["item_code"],
					"qty": item["qty"],
					"uom": frappe.db.get_value("Item", item["item_code"], "stock_uom"),
					"conversion_factor": 1,
					"allow_zero_valuation_rate": 1,
					required_field_name: warehouse_value
				})

			se.insert()
			se.submit()

		except Exception as e:
			frappe.log_error(f"Stock Entry Creation Failed for {self.name}", str(e))
			frappe.throw(f"Failed to create Stock Entry: {str(e)}")

	def create_journal_entry(self, claimed_items):
		if not claimed_items:
			return

		total_amount = 0
		for row in self.warranty_item_detail:
			if row.quantity_claimed > 0:
				total_amount += flt(row.quantity_claimed) * flt(row.rate)

		if total_amount == 0:
			return

		company = frappe.defaults.get_user_default("Company")
		if not company:
			frappe.throw("Please set a default Company in Global Defaults or User Defaults.")

		expense_account = frappe.db.get_value("Account", {"account_number": "1450", "company": company}, "name")
		if not expense_account:
			expense_account = frappe.db.get_value("Account", {"account_name": ["like", "%Warranty Sale Return%"], "company": company}, "name")
		
		if not expense_account:
			frappe.throw(f"Could not find Expense Account '1450 - Customer Warranty Sale Return' for company {company}.")

		customer_account = frappe.db.get_value("Account", {"account_number": "1310", "company": company}, "name")
		if not customer_account:
			frappe.throw(f"Could not determine Debtor Account for company {company}.")

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Credit Note"
		je.company = company
		je.posting_date = self.date
		je.remark = f"Credit Note for Warranty {self.name}"

		je.append("accounts", {
			"account": expense_account,
			"debit_in_account_currency": total_amount,
			"cost_center": frappe.get_value("Company", company, "cost_center")
		})

		je.append("accounts", {
			"account": customer_account,
			"credit_in_account_currency": total_amount,
			"party_type": "Customer",
			"party": self.customer
		})

		je.save()
		#je.submit()
		
		self.db_set("journal_entry", je.name)
		frappe.msgprint(f"✅ Journal Entry {je.name} created for Credit Note")

	def create_replacement_entries(self):
		received_items = self.get_received_items()
		claimed_items = self.get_claimed_items()

		self.create_stock_entry(
			"Material Receipt",
			received_items,
			warehouse_field="default_receipt_warehouse",
			required_field_name="to_warehouse"
		)
		self.create_stock_entry(
				"Material Issue",
				claimed_items,
				warehouse_field="default_claim_warehouse",
				required_field_name="from_warehouse"
			)

	def create_credit_entries(self):
		received_items = self.get_received_items()
		claimed_items = self.get_claimed_items()
		
		self.create_stock_entry(
			"Material Receipt",
			received_items,
			warehouse_field="default_receipt_warehouse",
			required_field_name="to_warehouse"
		)
		self.create_journal_entry(claimed_items)

	def set_pricing_details(self):
		if self.claim_settlement_type != "Credit Note" or not self.price_list:
			return

		company = frappe.defaults.get_user_default("Company")
		if not company:
			frappe.throw("Could not find default company")

		company_currency = frappe.db.get_value("Company", company, "default_currency")
		pl_currency = frappe.db.get_value("Price List", self.price_list, "currency") or company_currency

		for row in self.warranty_item_detail:
			if row.quantity_claimed > 0:
				item_uom = frappe.db.get_value("Item", row.item_code, "stock_uom")
				conversion_rate = 1.0
 
				
				args = {
					"item_code": row.item_code,
					"warehouse": self.default_claim_warehouse,
					"customer": self.customer,
					"selling_price_list": self.price_list,
					"price_list": self.price_list,
					"qty": row.quantity_claimed,
					"company": company,
					"doctype": "Sales Invoice",
					"name": self.name,
					"transaction_date": self.date or frappe.utils.today(),
					"currency": company_currency,
					"price_list_currency": pl_currency,
					"uom": item_uom,
					"stock_uom": item_uom,
					"conversion_factor": 1.0,
					"plc_conversion_rate": 1.0 if company_currency == pl_currency else None,
					"conversion_rate": 1.0 if company_currency == pl_currency else None,
				}
				
				details = get_item_details(args)
				frappe.msgprint(f"✅ Pricing details: {details}")
				
				if details:
					row.price_list_rate = details.get("price_list_rate")
					row.discount = details.get("discount_percentage")
					row.rate = row.price_list_rate * (1 - (row.discount / 100))
					row.amount = flt(row.rate) * flt(row.quantity_claimed)

	@frappe.whitelist()
	def get_credit_note_details_html(self):
		if self.claim_settlement_type != "Credit Note":
			return None

		company = frappe.defaults.get_user_default("Company")
		currency = frappe.db.get_value("Company", company, "default_currency")

		rows = []
		idx = 1
		total_amount = 0

		for row in self.warranty_item_detail:
			if row.quantity_claimed > 0:
				item_name = frappe.db.get_value("Item", row.item_code, "item_name")
				description = f"{row.item_code}: {item_name}"
				
				rows.append(f"""
					<tr>
						<td>{idx}</td>
						<td>{description}</td>
						<td style="text-align: right;">{flt(row.quantity_claimed, 2)}</td>
						<td style="text-align: right;">{frappe.format(row.price_list_rate, "Currency", currency=currency)}</td>
						<td style="text-align: right;">{flt(row.discount)}%</td>
						<td style="text-align: right;">{frappe.format(row.rate, "Currency", currency=currency)}</td>
						<td style="text-align: right;">{frappe.format(row.amount, "Currency", currency=currency)}</td>
					</tr>
				""")
				total_amount += row.amount
				idx += 1

		if not rows:
			return None

		# Using simpler HTML table structure as some editors strip thead/th or ignore colspan
		html = f"""
			<table class="table table-bordered" style="width: 100%; table-layout: fixed;">
				<tbody>
					<tr style="font-weight: bold;">
						<td style="width: 5%">S. No.</td>
						<td style="width: 45%">Item Code: Item Name</td>
						<td style="width: 10%; text-align: right;">Quantity Claimed</td>
						<td style="width: 15%; text-align: right;">Price List Rate</td>
						<td style="width: 10%; text-align: right;">Discount %</td>
						<td style="width: 15%; text-align: right;">Rate</td>
						<td style="width: 15%; text-align: right;">Amount</td>
					</tr>
					{"".join(rows)}
					<tr style="font-weight: bold">
						<td></td>
						<td></td>
						<td></td>
						<td></td>
						<td></td>
						<td style="text-align: right">Total</td>
						<td style="text-align: right">{frappe.format(total_amount, "Currency", currency=currency)}</td>
					</tr>
				</tbody>
			</table>
		"""
		
		return html