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

	def test_update_training_status_logs_real_reason(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Status Change Target",
				"personal_email": f"status-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.update_training_status("Training Cleared", reason="Cleared final viva on Day 21")
		trainee.reload()
		self.assertEqual(trainee.training_status, "Training Cleared")
		logs = frappe.get_all(
			"Sales Trainee Audit Log", filters={"trainee": trainee.name, "field_changed": "training_status"}
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(
			frappe.db.get_value("Sales Trainee Audit Log", logs[0].name, "reason"),
			"Cleared final viva on Day 21",
		)

	def test_update_training_status_requires_reason(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "No Reason Target",
				"personal_email": f"noreason-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.MandatoryError):
			trainee.update_training_status("Resigned", reason="")

	def test_exit_change_logged_separately_from_status(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exit Target",
				"personal_email": f"exit-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.update_training_status(
			"Resigned",
			reason="Resigned on Day 5, cited relocation",
			exit_status="Resigned",
			exit_date="2026-10-10",
			exit_reason="Relocation",
		)
		trainee.reload()
		self.assertEqual(trainee.exit_date, frappe.utils.getdate("2026-10-10"))
		field_names = set(
			frappe.get_all("Sales Trainee Audit Log", filters={"trainee": trainee.name}, pluck="field_changed")
		)
		self.assertIn("training_status", field_names)
		self.assertIn("exit_status", field_names)
		self.assertIn("exit_date", field_names)

	def test_direct_desk_edit_still_logged_with_fallback_reason(self):
		# Review Focus: a plain frappe.get_doc(...).save() from the Frappe desk
		# (not through update_training_status) must still leave an audit trail,
		# even though there is no reason field on that path.
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Desk Edit Target",
				"personal_email": f"desk-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.training_status = "Absconded"
		trainee.save(ignore_permissions=True)
		logs = frappe.get_all(
			"Sales Trainee Audit Log",
			filters={"trainee": trainee.name, "field_changed": "training_status"},
			fields=["reason"],
		)
		self.assertEqual(len(logs), 1)
		self.assertIn("direct edit", logs[0].reason.lower())
