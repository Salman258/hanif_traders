"""Seeds the Google Play reviewer sandbox account and synthetic complaint data.

Idempotent: each entity is created only if it does not already exist.

Seeded:
- User: google.reviewer@haniftraders.com
- Employee linked to that User
- Technician linked to that Employee with is_test_account=1
- 3 sample Complain records assigned to the Technician (varied statuses)

All customer fields are synthetic. The reviewer is filtered to only see
these records via the is_test_account checks in api/complain.py.
"""

import frappe
from frappe.utils import today, now_datetime


REVIEWER_EMAIL = "google.reviewer@haniftraders.com"
REVIEWER_FIRST_NAME = "Google"
REVIEWER_LAST_NAME = "Reviewer"
REVIEWER_FULL_NAME = f"{REVIEWER_FIRST_NAME} {REVIEWER_LAST_NAME}"


def _ensure_user():
	if frappe.db.exists("User", REVIEWER_EMAIL):
		return REVIEWER_EMAIL
	user = frappe.new_doc("User")
	user.email = REVIEWER_EMAIL
	user.first_name = REVIEWER_FIRST_NAME
	user.last_name = REVIEWER_LAST_NAME
	user.send_welcome_email = 0
	user.enabled = 1
	user.user_type = "System User"
	user.flags.ignore_permissions = True
	user.insert(ignore_permissions=True)
	return user.name


def _ensure_employee(user_id):
	existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
	if existing:
		return existing
	emp = frappe.new_doc("Employee")
	emp.first_name = REVIEWER_FIRST_NAME
	emp.last_name = REVIEWER_LAST_NAME
	emp.employee_name = REVIEWER_FULL_NAME
	emp.user_id = user_id
	emp.company_email = user_id
	emp.gender = frappe.db.get_value("Gender", {"name": "Male"}, "name") or frappe.db.get_value("Gender", {}, "name")
	emp.date_of_birth = "1990-01-01"
	emp.date_of_joining = today()
	emp.status = "Active"
	# Common custom fields used by this app's Employee customisations.
	for field, value in (
		("custom_cnic", "00000-0000000-0"),
		("custom_phone_number", "+92-300-0000000"),
		("custom_age", 30),
	):
		if hasattr(emp, field):
			setattr(emp, field, value)
	emp.flags.ignore_permissions = True
	emp.flags.ignore_mandatory = True
	emp.insert(ignore_permissions=True)
	return emp.name


def _ensure_technician(employee):
	if frappe.db.exists("Technician", employee):
		tech = frappe.get_doc("Technician", employee)
		if not tech.is_test_account:
			tech.is_test_account = 1
			tech.save(ignore_permissions=True)
		return tech.name
	tech = frappe.new_doc("Technician")
	tech.employee_id = employee
	tech.technician_name = REVIEWER_FULL_NAME
	tech.phone_number = "+92-300-0000000"
	tech.address = "Sandbox address — synthetic data"
	tech.is_test_account = 1
	tech.flags.ignore_permissions = True
	tech.flags.ignore_mandatory = True
	tech.insert(ignore_permissions=True)
	return tech.name


SAMPLE_COMPLAINTS = [
	{
		"__newname": "SANDBOX-DEMO-001",
		"complainer_name": "Test Customer 1",
		"complainer_phone": "+92-300-0000001",
		"complainer_address": "123 Sample Street, Demo Block, Test City",
		"instruction__remarks": "Refrigerator not cooling. Demo complaint for app review.",
		"workflow_state": "Assigned",
	},
	{
		"__newname": "SANDBOX-DEMO-002",
		"complainer_name": "Test Customer 2",
		"complainer_phone": "+92-300-0000002",
		"complainer_address": "456 Mock Avenue, Sample Town",
		"instruction__remarks": "AC making unusual noise. Demo complaint for app review.",
		"workflow_state": "Assigned",
	},
	{
		"__newname": "SANDBOX-DEMO-003",
		"complainer_name": "Test Customer 3",
		"complainer_phone": "+92-300-0000003",
		"complainer_address": "789 Synthetic Road, Example District",
		"instruction__remarks": "Washing machine drainage issue. Demo complaint for app review.",
		"workflow_state": "Resolved",
	},
]


def _seed_complaints(technician):
	# Only seed if this technician has no complaints at all (prevents duplicate
	# seeding on patch re-runs and on environments where the user adds their
	# own demo complaints later).
	existing = frappe.db.count("Complain", {"assigned_to_technician": technician})
	if existing:
		return

	for sample in SAMPLE_COMPLAINTS:
		newname = sample.pop("__newname")
		final_state = sample.pop("workflow_state")
		if frappe.db.exists("Complain", newname):
			continue
		# Workflow blocks direct state setting on insert, so insert in the
		# default Open state and then db_set the final state to bypass the
		# workflow validator.
		doc = frappe.new_doc("Complain")
		doc.name = newname
		doc.update(sample)
		doc.assigned_to_technician = technician
		doc.date = today()
		doc.posting_time = "09:00:00"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		try:
			doc.insert(ignore_permissions=True)
		except Exception as exc:
			frappe.log_error(
				title="seed_review_sandbox: complaint insert failed",
				message=f"{sample['complainer_name']}: {exc}",
			)
			continue

		updates = {"workflow_state": final_state, "status": final_state}
		if final_state == "Resolved":
			updates["resolution_date"] = today()
		frappe.db.set_value("Complain", newname, updates, update_modified=False)


def execute():
	user_id = _ensure_user()
	employee = _ensure_employee(user_id)
	technician = _ensure_technician(employee)
	_seed_complaints(technician)
	frappe.db.commit()
