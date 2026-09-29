import frappe
from frappe.tests import UnitTestCase


class TestSalesTraineeCohort(UnitTestCase):
	def test_create_cohort(self):
		name = f"Hyderabad-Oct-W1-{frappe.generate_hash(length=6)}"
		cohort = frappe.get_doc(
			{
				"doctype": "Sales Trainee Cohort",
				"cohort_name": name,
				"location": "Hyderabad",
				"start_date": "2026-10-06",
			}
		)
		cohort.insert(ignore_permissions=True)
		self.assertEqual(cohort.name, name)
		self.assertTrue(frappe.db.exists("Sales Trainee Cohort", name))

	def test_duplicate_cohort_name_rejected(self):
		name = f"Blr-Oct-W1-{frappe.generate_hash(length=6)}"
		frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": name, "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{"doctype": "Sales Trainee Cohort", "cohort_name": name, "start_date": "2026-10-13"}
			).insert(ignore_permissions=True)
