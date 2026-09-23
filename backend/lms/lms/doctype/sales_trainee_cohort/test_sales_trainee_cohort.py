import frappe
from frappe.tests import UnitTestCase


class TestSalesTraineeCohort(UnitTestCase):
	def test_create_cohort(self):
		cohort = frappe.get_doc(
			{
				"doctype": "Sales Trainee Cohort",
				"cohort_name": "Hyderabad-Oct-W1",
				"location": "Hyderabad",
				"start_date": "2026-10-06",
			}
		)
		cohort.insert(ignore_permissions=True)
		self.assertEqual(cohort.name, "Hyderabad-Oct-W1")
		self.assertTrue(frappe.db.exists("Sales Trainee Cohort", "Hyderabad-Oct-W1"))

	def test_duplicate_cohort_name_rejected(self):
		frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": "Blr-Oct-W1", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{"doctype": "Sales Trainee Cohort", "cohort_name": "Blr-Oct-W1", "start_date": "2026-10-13"}
			).insert(ignore_permissions=True)
