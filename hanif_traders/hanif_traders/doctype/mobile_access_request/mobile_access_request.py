# Copyright (c) 2025, Salman
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MobileAccessRequest(Document):

	def validate(self):
		if self.employee:
			self.erp_user = frappe.db.get_value("Employee", self.employee, "user_id")

		# Check status change without relying on workflow
		if self.status == "Approved" and self.db_get("status") != "Approved":
			self.approve_request()
		elif self.status == "Revoked" and self.db_get("status") != "Revoked":
			self.revoke_access()

	def approve_request(self):
		if not self.employee:
			frappe.throw("No Employee linked. Cannot approve request.")

		# Ensure the Employee has a User linked (create if missing)
		from hanif_traders.api.employee import create_user_for_employee
		erp_user = create_user_for_employee(self.employee)

		if not erp_user:
			frappe.throw("Could not create or find ERP User for this Employee.")
		
		from frappe.core.doctype.user.user import generate_keys
		key_data = generate_keys(erp_user)
		api_secret = key_data.get("api_secret")
		
		# Reload user to get the new API Key
		user_doc = frappe.get_doc("User", erp_user)
		# Store credentials on request (for mobile pickup)
		self.db_set({
			"api_key": user_doc.api_key,
			"api_secret": api_secret,
			"approved_by": frappe.session.user,
			"approved_on": now_datetime(),
		}, update_modified=False)
		
		frappe.msgprint(f"API Keys generated for {self.erp_user}")

	def revoke_access(self):
		if not self.erp_user:
			return

		user_doc = frappe.get_doc("User", self.erp_user)
		#user_docreset_api_secret()
		user_doc.api_key = None
		user_doc.api_secret = None
		user_doc.save(ignore_permissions=True)
		self.db_set({
			"api_key": None,
			"api_secret": None,
		}, update_modified=False)
		
		frappe.msgprint(f"API Keys revoked for {self.erp_user}")