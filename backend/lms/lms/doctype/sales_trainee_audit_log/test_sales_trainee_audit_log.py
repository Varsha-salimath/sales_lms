import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log


class TestSalesTraineeAuditLog(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Audit Target",
				"personal_email": f"audit-target-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_write_audit_log_records_reason(self):
		log = write_audit_log(
			trainee=self.trainee.name,
			field_changed="training_status",
			old_value="In Training",
			new_value="Training Cleared",
			reason="Cleared final viva",
		)
		self.assertEqual(log.reason, "Cleared final viva")
		self.assertEqual(log.trainee, self.trainee.name)

	def test_reason_is_mandatory(self):
		with self.assertRaises(frappe.MandatoryError):
			write_audit_log(
				trainee=self.trainee.name,
				field_changed="training_status",
				old_value="In Training",
				new_value="Resigned",
				reason="",
			)

	def test_audit_log_cannot_be_edited_after_creation(self):
		log = write_audit_log(
			trainee=self.trainee.name,
			field_changed="training_status",
			old_value="In Training",
			new_value="Resigned",
			reason="Resigned on Day 5",
		)
		log.reason = "Changed my mind"
		with self.assertRaises(frappe.ValidationError):
			log.save(ignore_permissions=True)
