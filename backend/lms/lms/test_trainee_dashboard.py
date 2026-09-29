# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_dashboard import get_dashboard_summary


class TestTraineeDashboard(UnitTestCase):
	def setUp(self):
		super().setUp()
		# get_dashboard_summary's Step-1-spec assertions count exact per-status totals.
		# Sales Trainee is a long-lived table that accumulates rows across this plan's
		# test runs (see progress.md's Task 8/Task 15 snapshot-pollution corrections),
		# so an unfiltered count is not safe against the shared clean-snapshot's
		# baseline rows. Scope every trainee (and every assertion) to a location unique
		# to this test run instead, which keeps the same per-status/total/payroll-eligible
		# assertions the brief specifies while staying immune to that accumulation.
		self.location = f"Dash-{frappe.generate_hash(length=6)}"
		for status in ("In Training", "Training Cleared", "Resigned", "Absconded"):
			frappe.get_doc(
				{
					"doctype": "Sales Trainee",
					"trainee_name": f"Dash {status}",
					"personal_email": f"dash-{status.lower().replace(' ', '')}-{frappe.generate_hash(length=6)}@example.com",
					"date_of_joining": "2026-10-06",
					"location": self.location,
					"training_status": status,
					"salary": 20000,
				}
			).insert(ignore_permissions=True)

	def test_summary_counts_every_status(self):
		summary = get_dashboard_summary(location=self.location)
		self.assertEqual(summary["in_training"], 1)
		self.assertEqual(summary["training_cleared"], 1)
		self.assertEqual(summary["resigned"], 1)
		self.assertEqual(summary["absconded"], 1)
		self.assertEqual(summary["total"], 4)

	def test_summary_filters_by_location(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Elsewhere",
				"personal_email": f"dash-elsewhere-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"location": f"{self.location}-elsewhere",
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		summary = get_dashboard_summary(location=self.location)
		self.assertEqual(summary["total"], 4)

	def test_summary_includes_payroll_eligible_count(self):
		summary = get_dashboard_summary(location=self.location)
		# Training Cleared trainees are payroll-eligible per spec §5/doc §5
		self.assertEqual(summary["payroll_eligible"], 1)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_summary_user_without_required_role_is_rejected(self):
		# Security Review Focus: get_dashboard_summary uses frappe.get_all, which
		# bypasses permission_query_conditions/has_permission hooks. A bare
		# @frappe.whitelist() with no access gate would let any authenticated user
		# read trainee headcounts. The gate mirrors Task 14's frontend nav-visibility
		# condition for this dashboard: Admin/Super Admin tier, or Sales Training
		# Leadership role.
		email = self._get_or_create_user(f"dashboard-no-access-{frappe.generate_hash(length=6)}@example.com")
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			get_dashboard_summary()
