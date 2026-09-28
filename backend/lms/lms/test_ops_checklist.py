"""Ops Checklist: per-user tour-skip state, and the role-scoped live checklist."""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import getdate

from lms.lms.ops_checklist import get_ops_checklist_tour_state, skip_ops_checklist_tour
from lms.lms.trainee_test_utils import make_user, run_as


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
