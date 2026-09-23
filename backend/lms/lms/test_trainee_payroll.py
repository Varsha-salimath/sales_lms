import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.trainee_payroll import compute_payable_days, prepare_weekly_inputs


class TestTraineePayroll(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Payable Days Target",
				"personal_email": f"payable-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"salary": 21000,
			}
		).insert(ignore_permissions=True)
		for day in range(6, 13):  # Oct 6-12
			status = "Present" if day != 9 else "Absent"
			mark(self.trainee.name, f"2026-10-{day:02d}", status, source="Manual")

	def test_compute_payable_days_counts_present_only(self):
		payable = compute_payable_days(self.trainee.name, "2026-10-06", "2026-10-12")
		self.assertEqual(payable, 6)  # 7 days marked, 1 Absent

	def test_compute_payable_days_stops_at_exit_date(self):
		# Review Focus: exiting mid-week must not count days after exit_date.
		self.trainee.exit_date = "2026-10-09"
		self.trainee.training_status = "Resigned"
		self.trainee.exit_status = "Resigned"
		self.trainee.save(ignore_permissions=True)
		payable = compute_payable_days(self.trainee.name, "2026-10-06", "2026-10-12")
		self.assertEqual(payable, 3)  # Oct 6,7,8 present, Oct 9 absent+exit, nothing after counts

	def test_prepare_weekly_inputs_fills_child_table(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		result = prepare_weekly_inputs(cycle.name)
		self.assertTrue(result["ok"])
		cycle.reload()
		row = next(r for r in cycle.payroll_inputs if r.trainee == self.trainee.name)
		self.assertEqual(row.payable_days, 6)
		self.assertEqual(row.salary, 21000)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_user_without_required_role_is_rejected(self):
		# Security Review Focus: a user with no System Manager / Sales Training Team /
		# Sales Training Finance role must not be able to prepare payroll inputs.
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		email = self._get_or_create_user(f"payroll-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			prepare_weekly_inputs(cycle.name)
