"""App Welcome Tour: per-user, one-time "seen the app tour" state."""

import frappe
from frappe.tests import UnitTestCase

from lms.lms.app_welcome_tour import get_app_welcome_tour_state, skip_app_welcome_tour
from lms.lms.trainee_test_utils import make_user, run_as


class TestAppWelcomeTourState(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.user = make_user("awt-user")

	def test_new_user_tour_is_not_skipped(self):
		run_as(self, self.user)
		state = get_app_welcome_tour_state()
		self.assertEqual(state["skipped"], False)
		self.assertIsNone(state["skipped_on"])

	def test_skip_tour_marks_it_skipped(self):
		run_as(self, self.user)
		skip_app_welcome_tour()
		state = get_app_welcome_tour_state()
		self.assertEqual(state["skipped"], True)
		self.assertIsNotNone(state["skipped_on"])

	def test_skip_tour_is_idempotent(self):
		run_as(self, self.user)
		skip_app_welcome_tour()
		# second call must not raise, and must not create a duplicate row
		skip_app_welcome_tour()
		count = frappe.db.count("App Welcome Tour State", {"user": self.user})
		self.assertEqual(count, 1)

	def test_guest_is_denied(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertRaises(frappe.PermissionError, get_app_welcome_tour_state)
		self.assertRaises(frappe.PermissionError, skip_app_welcome_tour)
