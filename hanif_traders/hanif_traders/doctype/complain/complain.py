# Copyright (c) 2025, Salman and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today


class Complain(Document):
	def validate(self):
		if self.workflow_state == "Assigned" and not self.assigned_to_technician:
			frappe.throw("Validate : Please assign a technician before setting status to Assigned.")

		if self.complainer_phone:
			duplicates = frappe.db.get_all(
				"Complain",
				filters={"complainer_phone": self.complainer_phone, "name": ["!=", self.name]},
				fields=["name", "date", "workflow_state"]
			)
			if duplicates:
				msg = "<b>Warning: Duplicate Phone Number</b><br>"
				msg += f"The phone number {self.complainer_phone} has been used in the following complaints:<br><ul>"
				for d in duplicates:
					msg += f"<li><a href='/app/complain/{d.name}'>{d.name}</a> ({d.date}) - {d.workflow_state}</li>"
				msg += "</ul>"
				frappe.msgprint(msg, title="Duplicate Complaint Warning", indicator="orange")

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

		old_tech = old.assigned_to_technician if old else None
		new_tech = self.assigned_to_technician
		old_name = frappe.db.get_value("Technician", old_tech, "technician_name") if old_tech else "Unknown"
		new_name = frappe.db.get_value("Technician", new_tech, "technician_name") if new_tech else "Unknown"

		# Fetch Settings
		settings = frappe.get_single("Complain Settings")
		if not settings.sms_enabled:
			return

		if new_state == "Open" and old_state != "Open":
			if settings.open_sms_template:
				msg = frappe.render_template(settings.open_sms_template, {"doc": self})

		elif new_state == "Assigned" and old_state != "Assigned":
			code_int = abs(hash(self.name + str(self.modified))) % 9000 + 1000
			csc = str(code_int)
			frappe.db.set_value("Complain", self.name, "complain_csc", csc)

			if settings.assigned_sms_template:
				msg = frappe.render_template(settings.assigned_sms_template, {"doc": self, "csc_code": csc})
		
		elif (new_state == "CSC Verified" and old_state != "CSC Verified") or (new_state == "Resolved" and old_state != "Resolved"):
			frappe.db.set_value("Complain", self.name, "resolution_date", today(), update_modified=False)
		
		if msg:
			try:
				from frappe.core.doctype.sms_settings.sms_settings import send_sms
				send_sms(receiver_list=[to_number], msg=msg)
				frappe.msgprint(f"✅ SMS Sent")
			except Exception as e:
				frappe.msgprint(f"❌ SMS Error: {e}")
		
		if old and old.assigned_to_technician != self.assigned_to_technician and old.assigned_to_technician and self.assigned_to_technician:
			self.add_comment("Comment", f"Technician changed from <b>{old_name}</b> to <b>{new_name}</b>")