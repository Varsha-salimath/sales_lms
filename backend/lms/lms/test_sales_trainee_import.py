import frappe
from frappe.tests import UnitTestCase

from lms.lms.sales_trainee_import import (
	commit_sales_trainee_import,
	get_sales_trainee_import_template_csv,
	import_sales_trainees,
	preview_sales_trainee_import,
)


def _csv(*rows):
	lines = ["Trainee Name,Personal Email,Phone,Location,Date of Joining,Salary,Cohort,TA SPOC"]
	lines.extend(rows)
	return "\n".join(lines)


class TestSalesTraineeImport(UnitTestCase):
	# --- legacy row-dict API (kept for direct callers / scripts) ---

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

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_user_without_required_role_is_rejected(self):
		# Security Review Focus: a user with no System Manager / Sales Training Team
		# role (e.g. read-only Sales Trainee Manager) must not be able to bulk-write
		# trainee records, even in dry_run mode.
		email = self._get_or_create_user(f"import-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			import_sales_trainees(rows=[self._row(f"blocked-{frappe.generate_hash(length=6)}@example.com")], dry_run=True)

	# --- new CSV upload flow (template / preview / commit), mirrors batch_enrollment_bulk.py ---

	def test_template_csv_has_expected_headers(self):
		csv_text = get_sales_trainee_import_template_csv()
		header = csv_text.strip().splitlines()[0]
		for label in ["Trainee Name", "Personal Email", "Date of Joining"]:
			self.assertIn(label, header)

	def test_template_csv_requires_import_role(self):
		email = self._get_or_create_user(f"template-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			get_sales_trainee_import_template_csv()

	def test_preview_flags_missing_mandatory_field(self):
		csv_text = _csv(",no-email@example.com,,,,,,")  # missing Trainee Name
		result = preview_sales_trainee_import(file_content=csv_text)
		self.assertEqual(len(result["errors"]), 1)
		self.assertTrue(any("trainee_name" in m for m in result["errors"][0]["messages"]))
		self.assertEqual(result["valid_count"], 0)

	def test_preview_flags_duplicate_rows_in_same_file(self):
		email = f"dupe-{frappe.generate_hash(length=6)}@example.com"
		csv_text = _csv(
			f"Dupe One,{email},,,2026-10-06,,,",
			f"Dupe Two,{email},,,2026-10-06,,,",
		)
		result = preview_sales_trainee_import(file_content=csv_text)
		self.assertEqual(len(result["errors"]), 1)  # 2nd occurrence errors, 1st is valid
		self.assertTrue(any("duplicate" in m.lower() for m in result["errors"][0]["messages"]))

	def test_preview_marks_existing_trainee_as_will_update(self):
		email = f"existing-{frappe.generate_hash(length=6)}@example.com"
		import_sales_trainees(rows=[self._row(email)], dry_run=False)
		csv_text = _csv(f"Existing Trainee,{email},,,2026-10-06,,,")
		result = preview_sales_trainee_import(file_content=csv_text)
		self.assertEqual(result["preview"][0]["status"], "will_update")

	def test_preview_marks_new_trainee_as_will_create(self):
		email = f"brandnew-{frappe.generate_hash(length=6)}@example.com"
		csv_text = _csv(f"Brand New,{email},,,2026-10-06,,,")
		result = preview_sales_trainee_import(file_content=csv_text)
		self.assertEqual(result["preview"][0]["status"], "will_create")

	def test_preview_rejects_xlsx_masquerading_as_csv(self):
		with self.assertRaises(frappe.ValidationError):
			preview_sales_trainee_import(file_content="PK\x03\x04fake-xlsx-bytes")

	def test_preview_requires_import_role(self):
		email = self._get_or_create_user(f"preview-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			preview_sales_trainee_import(file_content=_csv("A,b@example.com,,,2026-10-06,,,"))

	def test_commit_creates_and_updates_trainees(self):
		new_email = f"commit-new-{frappe.generate_hash(length=6)}@example.com"
		existing_email = f"commit-existing-{frappe.generate_hash(length=6)}@example.com"
		import_sales_trainees(rows=[self._row(existing_email, location="Pune")], dry_run=False)

		csv_text = _csv(
			f"New Trainee,{new_email},,Mumbai,2026-10-06,,,",
			f"Existing Trainee,{existing_email},,Bengaluru,2026-10-06,,,",
		)
		result = commit_sales_trainee_import(file_content=csv_text)
		self.assertEqual(result["created"], 1)
		self.assertEqual(result["updated"], 1)
		self.assertEqual(result["failed"], [])
		self.assertTrue(frappe.db.exists("Sales Trainee", {"personal_email": new_email}))
		self.assertEqual(
			frappe.db.get_value("Sales Trainee", {"personal_email": existing_email}, "location"), "Bengaluru"
		)

	def test_commit_blocks_when_rows_have_errors(self):
		csv_text = _csv(",missing-name@example.com,,,2026-10-06,,,")
		with self.assertRaises(frappe.ValidationError):
			commit_sales_trainee_import(file_content=csv_text)

	def test_commit_requires_import_role(self):
		email = self._get_or_create_user(f"commit-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			commit_sales_trainee_import(file_content=_csv(f"A,b-{frappe.generate_hash(length=6)}@example.com,,,2026-10-06,,,"))
