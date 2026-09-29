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


class TestPrepareWeeklyInputsSelection(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"I3-{frappe.generate_hash(length=6)}", "start_date": "2026-10-01"}
		).insert(ignore_permissions=True)

	def _trainee(self, label, **fields):
		return frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": label,
				"personal_email": f"i3-{frappe.generate_hash(length=8)}@example.com",
				"cohort": self.cohort.name,
				"salary": 20000,
				**fields,
			}
		).insert(ignore_permissions=True)

	def _cycle(self, **fields):
		return frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"cohort": self.cohort.name,
				**fields,
			}
		).insert(ignore_permissions=True)

	def test_mid_week_exit_gets_row_capped_at_exit_date(self):
		# I3: resigned on Thu Oct 9 after joining the week before. Must still get a row,
		# with working_days and payable_days both stopping at the exit date.
		trainee = self._trainee("Mid-week Exit", date_of_joining="2026-10-01")
		for day, status in ((6, "Present"), (7, "Present"), (8, "Present"), (9, "Absent"), (10, "Present")):
			mark(trainee.name, f"2026-10-{day:02d}", status, source="Manual")
		trainee.update_training_status(
			"Resigned", reason="Resigned mid-week", exit_status="Resigned", exit_date="2026-10-09"
		)
		cycle = self._cycle()
		prepare_weekly_inputs(cycle.name)
		cycle.reload()
		row = next(r for r in cycle.payroll_inputs if r.trainee == trainee.name)
		self.assertEqual(row.working_days, 4)  # Oct 6-9, not the full 7-day week
		self.assertEqual(row.payable_days, 3)  # Oct 10 "Present" is after exit, not counted

	def test_selection_uses_employment_overlap_not_status(self):
		exited_before = self._trainee(
			"Exited Before Week", date_of_joining="2026-09-20", training_status="Resigned", exit_date="2026-10-03"
		)
		joins_after = self._trainee("Joins After Week", date_of_joining="2026-10-13")
		cleared = self._trainee("Cleared Still Paid", date_of_joining="2026-10-01", training_status="Training Cleared")
		cycle = self._cycle()
		prepare_weekly_inputs(cycle.name)
		cycle.reload()
		included = {r.trainee for r in cycle.payroll_inputs}
		self.assertIn(cleared.name, included)
		self.assertNotIn(exited_before.name, included)
		self.assertNotIn(joins_after.name, included)
		row = next(r for r in cycle.payroll_inputs if r.trainee == cleared.name)
		self.assertEqual(row.working_days, 7)

	def test_rejects_cycle_past_preparing_and_keeps_inputs(self):
		# I4: re-running prep on a Shared cycle must not wipe Finance's notes.
		trainee = self._trainee("Shared Cycle Row", date_of_joining="2026-10-01")
		cycle = self._cycle(
			status="Shared with Vendor",
			payroll_inputs=[
				{
					"trainee": trainee.name,
					"salary": 20000,
					"working_days": 7,
					"payable_days": 5,
					"joining_or_exit_adjustment_note": "Finance: 2 days held back",
				}
			],
		)
		with self.assertRaises(frappe.ValidationError) as ctx:
			prepare_weekly_inputs(cycle.name)
		self.assertNotIsInstance(ctx.exception, frappe.PermissionError)
		cycle.reload()
		self.assertEqual(len(cycle.payroll_inputs), 1)
		self.assertEqual(cycle.payroll_inputs[0].joining_or_exit_adjustment_note, "Finance: 2 days held back")
		self.assertEqual(cycle.payroll_inputs[0].payable_days, 5)
