import base64
import io

import frappe
import openpyxl
from frappe.tests import UnitTestCase

from lms.lms.trainee_reports import export_active_trainees_csv


class TestTraineeReports(UnitTestCase):
	def test_export_includes_only_in_training_trainees(self):
		active = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Active One",
				"personal_email": f"active-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		exited = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exited One",
				"personal_email": f"exited-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "Resigned",
			}
		).insert(ignore_permissions=True)

		encoded = export_active_trainees_csv()
		workbook = openpyxl.load_workbook(io.BytesIO(base64.b64decode(encoded)))
		sheet = workbook.active
		names_in_sheet = {row[0].value for row in sheet.iter_rows(min_row=2)}
		self.assertIn(active.trainee_name, names_in_sheet)
		self.assertNotIn(exited.trainee_name, names_in_sheet)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_user_without_required_role_is_rejected(self):
		# Security Review Focus: export_active_trainees_csv uses frappe.get_all,
		# which bypasses permission_query_conditions/has_permission hooks. A bare
		# @frappe.whitelist() with no role gate would let any authenticated user
		# dump PII (personal emails, locations) for all active trainees.
		email = self._get_or_create_user(f"report-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			export_active_trainees_csv()
