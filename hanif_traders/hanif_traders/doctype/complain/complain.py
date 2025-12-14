# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Complain(Document):
	def validate(self):
		if self.workflow_state == "Assigned" and not self.assigned_to_technician:
			frappe.throw("Validate : Please assign a technician before setting status to Assigned.")

	def before_save(self):
		if self.workflow_state in ["Resolved", "CSC Verified"]:
			from frappe.utils import time_diff_in_hours, now_datetime, get_datetime
			
			if self.date and self.posting_time:
				start_time = get_datetime(f"{self.date} {self.posting_time}")
			else:
				start_time = self.creation

			time_taken = time_diff_in_hours(now_datetime(), start_time)
			
			# Convert to Hours.Minutes (e.g., 1.5 hours -> 1.30)
			hours = int(time_taken)
			minutes = (time_taken - hours) * 60
			self.time_to_resolution = hours + (minutes / 100)

	def on_update(self):
		old = self.get_doc_before_save()
		if not self.complainer_phone:
			return

		to_number = self.complainer_phone.replace("+92-", "0")
		new_state = self.workflow_state
		old_state = old.workflow_state if old else None
		msg = None

		if new_state == "Open" and old_state != "Open":
			msg = (
				f"Dear customer, your complaint no. {self.name} "
				"has been registered at GFC Service Center Karachi. Estimated resolution time is 48 hours."
			)

		elif new_state == "Assigned" and old_state != "Assigned":
			code_int = abs(hash(self.name + str(self.modified))) % 9000 + 1000
			csc = str(code_int)
			frappe.db.set_value("Complain", self.name, "complain_csc", csc)

			msg = (
				f"Validate: Dear customer, technician is assigned to your complaint "
				f"(No. {self.name}). Please provide code {csc} "
				"to the technician if you’re satisfied with our service."
			)

		if msg:
			try:
				from frappe.core.doctype.sms_settings.sms_settings import send_sms
				send_sms(receiver_list=[to_number], msg=msg)
				frappe.msgprint(f"✅ SMS Sent: {msg}")
			except Exception as e:
				frappe.msgprint(f"❌ SMS Error: {e}")
