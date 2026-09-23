import frappe
from frappe.tests import UnitTestCase

from lms.lms.sales_trainee_import import import_sales_trainees


class TestSalesTraineeImport(UnitTestCase):
	def _row(self, email, **overrides):
		row = {
			"trainee_name": "Import Target",
			"personal_email": email,
			"phone": "9999999999",
			"date_of_joining": "2026-10-06",
		}
		row.update(overrides)
		return row

	def test_dry_run_flags_missing_mandatory_field(self):
		result = import_sales_trainees(
			rows=[{"trainee_name": "No Email", "date_of_joining": "2026-10-06"}], dry_run=True
		)
		self.assertFalse(result["ok"])
		self.assertTrue(any("personal_email" in e for e in result["errors"]))
		self.assertFalse(frappe.db.exists("Sales Trainee", {"trainee_name": "No Email"}))

	def test_dry_run_flags_duplicate_rows_in_same_batch(self):
		email = f"dupe-{frappe.generate_hash(length=6)}@example.com"
		result = import_sales_trainees(rows=[self._row(email), self._row(email)], dry_run=True)
		self.assertFalse(result["ok"])
		self.assertTrue(any("duplicate" in e.lower() for e in result["errors"]))

	def test_real_run_creates_trainee(self):
		email = f"create-{frappe.generate_hash(length=6)}@example.com"
		result = import_sales_trainees(rows=[self._row(email)], dry_run=False)
		self.assertTrue(result["ok"])
		self.assertEqual(result["created"], 1)
		self.assertTrue(frappe.db.exists("Sales Trainee", {"personal_email": email}))

	def test_re_upload_of_existing_email_updates_not_duplicates(self):
		# Review Focus: re-uploading (or moving cohort) must upsert, never create a
		# second Sales Trainee for the same person.
		email = f"reupload-{frappe.generate_hash(length=6)}@example.com"
		import_sales_trainees(rows=[self._row(email, location="Pune")], dry_run=False)
		result = import_sales_trainees(rows=[self._row(email, location="Bengaluru")], dry_run=False)
		self.assertTrue(result["ok"])
		self.assertEqual(result["updated"], 1)
		matches = frappe.get_all("Sales Trainee", filters={"personal_email": email})
		self.assertEqual(len(matches), 1)
		self.assertEqual(frappe.db.get_value("Sales Trainee", matches[0].name, "location"), "Bengaluru")
