"""C1 regressions: whitelisted Document methods reached through run_doc_method
(which only checks READ on load) must still enforce WRITE, per role."""

import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.trainee_test_utils import call_doc_method, make_trainee, make_user, run_as


def _cycle(status="Preparing"):
	return frappe.get_doc(
		{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12", "status": status}
	).insert(ignore_permissions=True)


class TestAdvanceStatusAccess(UnitTestCase):
	def test_read_only_leadership_cannot_advance(self):
		cycle = _cycle()
		run_as(self, make_user("c1-leadership", "Sales Training Leadership"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method("Weekly Payroll Cycle", cycle.name, "advance_status", new_status="Ready to Share")
		self.assertEqual(frappe.db.get_value("Weekly Payroll Cycle", cycle.name, "status"), "Preparing")

	def test_read_only_leadership_cannot_close(self):
		cycle = _cycle("Finance Validation")
		run_as(self, make_user("c1-leadership-close", "Sales Training Leadership"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method("Weekly Payroll Cycle", cycle.name, "advance_status", new_status="Closed")
		self.assertIsNone(frappe.db.get_value("Weekly Payroll Cycle", cycle.name, "finance_validated_by"))

	def test_training_team_can_advance_but_not_close(self):
		team = make_user("c1-team", "Sales Training Team")
		cycle = _cycle()
		run_as(self, team)
		call_doc_method("Weekly Payroll Cycle", cycle.name, "advance_status", new_status="Ready to Share")
		self.assertEqual(frappe.db.get_value("Weekly Payroll Cycle", cycle.name, "status"), "Ready to Share")

		frappe.set_user("Administrator")
		to_close = _cycle("Finance Validation")
		frappe.set_user(team)
		with self.assertRaises(frappe.PermissionError):
			call_doc_method("Weekly Payroll Cycle", to_close.name, "advance_status", new_status="Closed")
		self.assertEqual(frappe.db.get_value("Weekly Payroll Cycle", to_close.name, "status"), "Finance Validation")

	def test_finance_can_close_and_is_stamped(self):
		finance = make_user("c1-finance", "Sales Training Finance")
		cycle = _cycle("Finance Validation")
		run_as(self, finance)
		call_doc_method("Weekly Payroll Cycle", cycle.name, "advance_status", new_status="Closed")
		status, validated_by = frappe.db.get_value(
			"Weekly Payroll Cycle", cycle.name, ["status", "finance_validated_by"]
		)
		self.assertEqual(status, "Closed")
		self.assertEqual(validated_by, finance)


class TestUpdateTrainingStatusAccess(UnitTestCase):
	def test_read_only_leadership_cannot_change_status(self):
		trainee = make_trainee("C1 Status Leadership")
		run_as(self, make_user("c1-status-leadership", "Sales Training Leadership"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method(
				"Sales Trainee", trainee.name, "update_training_status", new_status="Absconded", reason="probe"
			)
		self.assertEqual(frappe.db.get_value("Sales Trainee", trainee.name, "training_status"), "In Training")

	def test_read_only_finance_cannot_change_status(self):
		trainee = make_trainee("C1 Status Finance")
		run_as(self, make_user("c1-status-finance", "Sales Training Finance"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method(
				"Sales Trainee", trainee.name, "update_training_status", new_status="Resigned", reason="probe"
			)
		self.assertEqual(frappe.db.get_value("Sales Trainee", trainee.name, "training_status"), "In Training")

	def test_manager_can_change_own_trainee_status(self):
		manager = make_user("c1-status-manager", "Sales Trainee Manager")
		trainee = make_trainee("C1 Status Own", assigned_sales_manager=manager)
		run_as(self, manager)
		call_doc_method(
			"Sales Trainee", trainee.name, "update_training_status", new_status="Training Cleared", reason="Cleared viva"
		)
		self.assertEqual(frappe.db.get_value("Sales Trainee", trainee.name, "training_status"), "Training Cleared")

	def test_manager_cannot_change_other_managers_trainee(self):
		manager = make_user("c1-status-manager-a", "Sales Trainee Manager")
		other = make_user("c1-status-manager-b", "Sales Trainee Manager")
		trainee = make_trainee("C1 Status Other", assigned_sales_manager=other)
		run_as(self, manager)
		with self.assertRaises(frappe.PermissionError):
			call_doc_method(
				"Sales Trainee", trainee.name, "update_training_status", new_status="Absconded", reason="probe"
			)


class TestCorrectAttendanceAccess(UnitTestCase):
	def test_read_only_finance_cannot_correct(self):
		trainee = make_trainee("C1 Correct Finance")
		row = mark(trainee.name, "2026-10-06", "Absent")
		run_as(self, make_user("c1-correct-finance", "Sales Training Finance"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method("Sales Trainee Attendance", row.name, "correct", new_status="Present", reason="probe")
		self.assertEqual(frappe.db.get_value("Sales Trainee Attendance", row.name, "status"), "Absent")

	def test_read_only_leadership_cannot_correct(self):
		trainee = make_trainee("C1 Correct Leadership")
		row = mark(trainee.name, "2026-10-06", "Absent")
		run_as(self, make_user("c1-correct-leadership", "Sales Training Leadership"))
		with self.assertRaises(frappe.PermissionError):
			call_doc_method("Sales Trainee Attendance", row.name, "correct", new_status="Present", reason="probe")
		self.assertEqual(frappe.db.get_value("Sales Trainee Attendance", row.name, "status"), "Absent")

	def test_manager_can_correct_own_trainee(self):
		manager = make_user("c1-correct-manager", "Sales Trainee Manager")
		trainee = make_trainee("C1 Correct Own", assigned_sales_manager=manager)
		row = mark(trainee.name, "2026-10-06", "Absent")
		run_as(self, manager)
		call_doc_method("Sales Trainee Attendance", row.name, "correct", new_status="Present", reason="Was present")
		self.assertEqual(frappe.db.get_value("Sales Trainee Attendance", row.name, "status"), "Present")
