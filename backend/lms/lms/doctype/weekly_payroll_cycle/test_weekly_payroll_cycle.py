import frappe
from frappe.tests import UnitTestCase


class TestWeeklyPayrollCycle(UnitTestCase):
	def test_create_cycle_defaults_to_preparing(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		)
		cycle.insert(ignore_permissions=True)
		self.assertEqual(cycle.status, "Preparing")

	def test_advance_status_follows_sequence(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		cycle.advance_status("Ready to Share")
		cycle.reload()
		self.assertEqual(cycle.status, "Ready to Share")

	def test_advance_status_rejects_skipping_a_step(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			cycle.advance_status("Closed")

	def test_payroll_input_child_rows(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Payroll Target",
				"personal_email": f"payroll-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"salary": 25000,
			}
		).insert(ignore_permissions=True)
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"payroll_inputs": [
					{"trainee": trainee.name, "salary": 25000, "working_days": 6, "payable_days": 6}
				],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(len(cycle.payroll_inputs), 1)
		self.assertEqual(cycle.payroll_inputs[0].payable_days, 6)
