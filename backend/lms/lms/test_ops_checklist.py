"""Ops Checklist: per-user tour-skip state, and the role-scoped live checklist."""

from datetime import date

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import getdate

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.ops_checklist import get_ops_checklist_tour_state, skip_ops_checklist_tour, get_ops_checklist
from lms.lms.trainee_test_utils import make_trainee, make_user, run_as


class TestOpsChecklistTourState(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.user = make_user("occ-tour", "Sales Training Team")

	def test_new_user_tour_is_not_skipped(self):
		run_as(self, self.user)
		state = get_ops_checklist_tour_state()
		self.assertEqual(state["skipped"], False)
		self.assertIsNone(state["skipped_on"])

	def test_skip_tour_marks_it_skipped(self):
		run_as(self, self.user)
		skip_ops_checklist_tour()
		state = get_ops_checklist_tour_state()
		self.assertEqual(state["skipped"], True)
		self.assertIsNotNone(state["skipped_on"])

	def test_skip_tour_is_idempotent(self):
		run_as(self, self.user)
		skip_ops_checklist_tour()
		# second call must not raise, and must not create a duplicate row
		skip_ops_checklist_tour()
		count = frappe.db.count("Ops Checklist Tour State", {"user": self.user})
		self.assertEqual(count, 1)

	def test_guest_is_denied(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertRaises(frappe.PermissionError, get_ops_checklist_tour_state)
		self.assertRaises(frappe.PermissionError, skip_ops_checklist_tour)


class TestOpsChecklistAggregator(UnitTestCase):
	def setUp(self):
		super().setUp()
		tag = frappe.generate_hash(length=6)
		self.today = date.today().isoformat()
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"OCC-{tag}", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		self.manager = make_user("occ-manager", "Sales Trainee Manager")
		self.finance_user = make_user("occ-finance", "Sales Training Finance")
		self.leadership_user = make_user("occ-lead", "Sales Training Leadership")
		self.team_user = make_user("occ-team", "Sales Training Team")
		self.trainee = make_trainee(f"OCC Mine {tag}", assigned_sales_manager=self.manager, cohort=self.cohort.name)

	def test_team_role_sees_missing_attendance_for_the_cohort(self):
		run_as(self, self.team_user)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_manager_with_no_trainees_gets_no_attendance_items(self):
		other_manager = make_user("occ-manager-empty", "Sales Trainee Manager")
		run_as(self, other_manager)
		result = get_ops_checklist()
		self.assertEqual(result["items"], [])

	def test_manager_is_scoped_to_their_own_trainees(self):
		run_as(self, self.manager)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_marking_attendance_clears_the_item(self):
		mark(self.trainee.name, self.today, "Present")
		run_as(self, self.manager)
		result = get_ops_checklist()
		self.assertFalse(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_finance_role_sees_open_cycle_item(self):
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"cohort": self.cohort.name,
				"status": "Preparing",
			}
		).insert(ignore_permissions=True)
		run_as(self, self.finance_user)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"cycle:{cycle.name}" for item in result["items"]))

	def test_leadership_role_gets_summary_not_action_items(self):
		run_as(self, self.leadership_user)
		result = get_ops_checklist()
		self.assertEqual(result["items"], [])
		self.assertIsNotNone(result["summary"])
		self.assertIn("total", result["summary"])

	def test_admin_with_scoped_role_sees_org_wide_view_not_empty_scope(self):
		admin_with_manager_role = make_user("occ-admin-manager", "Sales Trainee Manager")
		frappe.get_doc("User", admin_with_manager_role).add_roles("System Manager")
		run_as(self, admin_with_manager_role)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_user_without_any_sales_role_is_denied(self):
		bystander = make_user("occ-bystander")
		run_as(self, bystander)
		self.assertRaises(frappe.PermissionError, get_ops_checklist)

	def test_payroll_deadline_item_present_and_well_formed(self):
		run_as(self, self.team_user)
		result = get_ops_checklist()
		deadline_items = [item for item in result["items"] if item["key"] == "payroll-deadline"]
		self.assertEqual(len(deadline_items), 1)
		self.assertIn("day", deadline_items[0]["title"])


class TestPayrollDeadlineMath(UnitTestCase):
	"""Direct tests of the date math, independent of "today" — the aggregator test
	above only proves an item exists, not that month-boundary rollover is correct."""

	def test_deadline_on_or_before_the_25th_is_this_month(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-10"))[0]
		self.assertIn("2026-09-25", item["title"])

	def test_deadline_after_the_25th_rolls_over_to_next_month(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-28"))[0]
		self.assertIn("2026-10-25", item["title"])
		self.assertIn("27 day(s) left", item["title"])

	def test_deadline_on_the_25th_itself_is_zero_days_left(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-25"))[0]
		self.assertIn("0 day(s) left", item["title"])
