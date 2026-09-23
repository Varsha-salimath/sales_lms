"""I1/I2 regressions, run WITH the real Sales Training roles: reports, stats and
attendance marking must respect the reporting-tree scope, and the onboarding
team must see the unassigned trainees it imports."""

import base64
import io

import frappe
import openpyxl
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark, mark_attendance
from lms.lms.trainee_cohort_stats import get_cohort_stats, list_missing_attendance
from lms.lms.trainee_reports import (
	export_active_trainees_csv,
	export_exit_churn_report,
	export_training_outcome_report,
	export_weekly_attendance_payroll_report,
)
from lms.lms.trainee_test_utils import make_trainee, make_user, run_as


def _first_column(encoded):
	sheet = openpyxl.load_workbook(io.BytesIO(base64.b64decode(encoded))).active
	return {row[0].value for row in sheet.iter_rows(min_row=2)}


class TestManagerScopedEndpoints(UnitTestCase):
	def setUp(self):
		super().setUp()
		tag = frappe.generate_hash(length=6)
		self.manager_a = make_user("i1-manager-a", "Sales Trainee Manager")
		self.manager_b = make_user("i1-manager-b", "Sales Trainee Manager")
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"I1-Scope-{tag}", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		self.mine = make_trainee(f"I1 Mine {tag}", assigned_sales_manager=self.manager_a, cohort=self.cohort.name)
		self.theirs = make_trainee(f"I1 Theirs {tag}", assigned_sales_manager=self.manager_b, cohort=self.cohort.name)
		self.mine_exited = make_trainee(
			f"I1 Mine Exited {tag}", assigned_sales_manager=self.manager_a, training_status="Resigned"
		)
		self.theirs_exited = make_trainee(
			f"I1 Theirs Exited {tag}", assigned_sales_manager=self.manager_b, training_status="Resigned"
		)
		mark(self.mine.name, "2026-10-06", "Present")
		mark(self.theirs.name, "2026-10-06", "Present")

	def test_active_trainees_export_is_scoped(self):
		run_as(self, self.manager_a)
		names = _first_column(export_active_trainees_csv(cohort=self.cohort.name))
		self.assertIn(self.mine.trainee_name, names)
		self.assertNotIn(self.theirs.trainee_name, names)

	def test_training_outcome_export_is_scoped(self):
		run_as(self, self.manager_a)
		names = _first_column(export_training_outcome_report(cohort=self.cohort.name))
		self.assertIn(self.mine.trainee_name, names)
		self.assertNotIn(self.theirs.trainee_name, names)

	def test_exit_churn_export_is_scoped(self):
		run_as(self, self.manager_a)
		names = _first_column(export_exit_churn_report())
		self.assertIn(self.mine_exited.trainee_name, names)
		self.assertNotIn(self.theirs_exited.trainee_name, names)

	def test_weekly_attendance_export_is_scoped(self):
		run_as(self, self.manager_a)
		trainees = _first_column(export_weekly_attendance_payroll_report("2026-10-06", "2026-10-12"))
		self.assertIn(self.mine.name, trainees)
		self.assertNotIn(self.theirs.name, trainees)

	def test_cohort_stats_are_scoped(self):
		run_as(self, self.manager_a)
		self.assertEqual(get_cohort_stats(self.cohort.name)["total"], 1)

	def test_missing_attendance_is_scoped(self):
		run_as(self, self.manager_a)
		missing = list_missing_attendance("2026-10-07", cohort=self.cohort.name)
		self.assertEqual(missing, [self.mine.name])

	def test_manager_can_mark_own_trainee(self):
		run_as(self, self.manager_a)
		result = mark_attendance(self.mine.name, "2026-10-08", "Present")
		self.assertEqual(result["status"], "Present")

	def test_manager_cannot_mark_other_managers_trainee(self):
		run_as(self, self.manager_a)
		with self.assertRaises(frappe.PermissionError):
			mark_attendance(self.theirs.name, "2026-10-08", "Present")
		self.assertFalse(
			frappe.db.exists("Sales Trainee Attendance", {"trainee": self.theirs.name, "attendance_date": "2026-10-08"})
		)

	def test_leadership_still_sees_everything(self):
		run_as(self, make_user("i1-leadership", "Sales Training Leadership"))
		self.assertEqual(get_cohort_stats(self.cohort.name)["total"], 2)


class TestTrainingTeamVisibility(UnitTestCase):
	def test_team_sees_unassigned_imported_trainee(self):
		# The exact shape sales_trainee_import.py produces: no assigned_trainer and
		# no assigned_sales_manager.
		trainee = make_trainee(f"I2 Unassigned {frappe.generate_hash(length=6)}")
		run_as(self, make_user("i2-team", "Sales Training Team"))
		visible = frappe.get_list("Sales Trainee", filters={"name": trainee.name}, pluck="name")
		self.assertEqual(visible, [trainee.name])
		self.assertTrue(frappe.has_permission("Sales Trainee", "read", doc=trainee.name))

	def test_team_can_mark_unassigned_trainee(self):
		trainee = make_trainee(f"I2 Mark {frappe.generate_hash(length=6)}")
		run_as(self, make_user("i2-team-mark", "Sales Training Team"))
		result = mark_attendance(trainee.name, "2026-10-06", "Present")
		self.assertEqual(result["status"], "Present")

	def test_manager_still_does_not_see_unassigned_trainee(self):
		trainee = make_trainee(f"I2 Hidden {frappe.generate_hash(length=6)}")
		run_as(self, make_user("i2-manager", "Sales Trainee Manager"))
		visible = frappe.get_list("Sales Trainee", filters={"name": trainee.name}, pluck="name")
		self.assertEqual(visible, [])
