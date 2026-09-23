import frappe
from frappe.tests import UnitTestCase


class TestSalesTrainee(UnitTestCase):
	def test_create_trainee_defaults_to_in_training(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Asha Rao",
				"personal_email": "asha.rao.candidate@example.com",
				"phone": "9876543210",
				"date_of_joining": "2026-10-06",
			}
		)
		trainee.insert(ignore_permissions=True)
		self.assertEqual(trainee.training_status, "In Training")
		self.assertEqual(trainee.employee_dummy_vendor_code, None)

	def test_duplicate_email_rejected(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "First",
				"personal_email": "dup@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.UniqueValidationError):
			frappe.get_doc(
				{
					"doctype": "Sales Trainee",
					"trainee_name": "Second",
					"personal_email": "dup@example.com",
					"date_of_joining": "2026-10-06",
				}
			).insert(ignore_permissions=True)

	def test_no_user_link_field_exists(self):
		meta = frappe.get_meta("Sales Trainee")
		for field in meta.fields:
			if field.fieldtype == "Link" and field.options == "User":
				continue  # ta_spoc / assigned_trainer / assigned_sales_manager are expected staff links
			self.assertNotEqual(
				(field.fieldtype, field.options), ("Link", "User"),
				"Sales Trainee must stay standalone for the trainee identity itself",
			)
