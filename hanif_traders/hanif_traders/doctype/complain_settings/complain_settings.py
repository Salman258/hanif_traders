# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ComplainSettings(Document):
	def validate(self):
		if self.enable_currency_incentive and self.enable_point_incentive:
			frappe.throw("You can only enable one type of incentive (Currency or Points) at a time.")
