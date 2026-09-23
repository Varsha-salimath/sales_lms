import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark


class TestSalesTraineeAttendance(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Attendance Target",
				"personal_email": f"attendance-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_mark_creates_one_row(self):
		row = mark(self.trainee.name, "2026-10-06", "Present", source="Manual")
		self.assertEqual(row.status, "Present")
		self.assertEqual(row.source, "Manual")
		count = frappe.db.count(
			"Sales Trainee Attendance", {"trainee": self.trainee.name, "attendance_date": "2026-10-06"}
		)
		self.assertEqual(count, 1)

	def test_marking_same_trainee_date_twice_updates_not_duplicates(self):
		mark(self.trainee.name, "2026-10-07", "Present", source="Manual")
		mark(self.trainee.name, "2026-10-07", "Absent", source="Manual")
		rows = frappe.get_all(
			"Sales Trainee Attendance", filters={"trainee": self.trainee.name, "attendance_date": "2026-10-07"}
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(frappe.db.get_value("Sales Trainee Attendance", rows[0].name, "status"), "Absent")

	def test_correct_writes_audit_log_with_reason(self):
		row = mark(self.trainee.name, "2026-10-08", "Absent", source="Manual")
		row.correct("Present", reason="Trainee was present, marked absent by mistake")
		row.reload()
		self.assertEqual(row.status, "Present")
		logs = frappe.get_all(
			"Sales Trainee Audit Log",
			filters={"trainee": self.trainee.name, "field_changed": f"attendance:{row.name}"},
		)
		self.assertEqual(len(logs), 1)

	def test_correct_requires_reason(self):
		row = mark(self.trainee.name, "2026-10-09", "Absent", source="Manual")
		with self.assertRaises(frappe.MandatoryError):
			row.correct("Present", reason="")

	def test_correction_allowed_after_payroll_cycle_closed(self):
		# Review Focus: closing a cycle must not trap Training Team out of fixing a mistake.
		row = mark(self.trainee.name, "2026-10-10", "Absent", source="Manual")
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"status": "Closed",
			}
		).insert(ignore_permissions=True)
		row.correct("Present", reason="Late correction after cycle closed")
		row.reload()
		self.assertEqual(row.status, "Present")
		self.assertIn("Closed", cycle.status)  # cycle itself is untouched, correction just logs
