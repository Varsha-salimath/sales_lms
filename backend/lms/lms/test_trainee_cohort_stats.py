import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.trainee_cohort_stats import get_cohort_stats, list_missing_attendance


class TestTraineeCohortStats(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"Stats-Cohort-{frappe.generate_hash(length=6)}", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		self.active = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Active",
				"personal_email": f"stats-active-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"cohort": self.cohort.name,
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		self.exited = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exited",
				"personal_email": f"stats-exited-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"cohort": self.cohort.name,
				"training_status": "Resigned",
			}
		).insert(ignore_permissions=True)

	def test_get_cohort_stats_counts_by_status(self):
		stats = get_cohort_stats(self.cohort.name)
		self.assertEqual(stats["total"], 2)
		self.assertEqual(stats["active"], 1)
		self.assertEqual(stats["exits"], 1)

	def test_list_missing_attendance_flags_unmarked_active_trainee(self):
		mark(self.exited.name, "2026-10-08", "Present")  # exited trainee not in scope anyway
		missing = list_missing_attendance("2026-10-08", cohort=self.cohort.name)
		self.assertIn(self.active.name, missing)

	def test_list_missing_attendance_excludes_marked_trainee(self):
		mark(self.active.name, "2026-10-09", "Present")
		missing = list_missing_attendance("2026-10-09", cohort=self.cohort.name)
		self.assertNotIn(self.active.name, missing)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_get_cohort_stats_user_without_required_role_is_rejected(self):
		# Security Review Focus: get_cohort_stats uses frappe.get_all, which bypasses
		# permission_query_conditions/has_permission hooks. A bare @frappe.whitelist()
		# with no role gate would let any authenticated user read cohort headcounts.
		email = self._get_or_create_user(f"cohort-stats-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			get_cohort_stats(self.cohort.name)

	def test_list_missing_attendance_user_without_required_role_is_rejected(self):
		# Security Review Focus: list_missing_attendance uses frappe.get_all, which
		# bypasses permission_query_conditions/has_permission hooks. A bare
		# @frappe.whitelist() with no role gate would let any authenticated user
		# enumerate trainee names by attendance status.
		email = self._get_or_create_user(f"missing-attendance-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			list_missing_attendance("2026-10-08", cohort=self.cohort.name)
