import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_scope import sales_trainee_query_conditions


class TestTraineeScope(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.manager = self._get_or_create_user("trainee-scope-manager@example.com")
		self.other_manager = self._get_or_create_user("trainee-scope-other-manager@example.com")
		self.trainee_with_manager = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Managed Trainee",
				"personal_email": f"managed-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_sales_manager": self.manager,
			}
		).insert(ignore_permissions=True)
		self.trainee_no_manager_yet = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Unassigned Trainee",
				"personal_email": f"unassigned-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_trainer": self.manager,
			}
		).insert(ignore_permissions=True)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_manager_sees_assigned_trainee(self):
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608 - condition is server-built, not user input
		)
		names = {row.name for row in visible}
		self.assertIn(self.trainee_with_manager.name, names)

	def test_manager_does_not_see_unrelated_trainee(self):
		other_trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Someone Else's Trainee",
				"personal_email": f"else-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_sales_manager": self.other_manager,
			}
		).insert(ignore_permissions=True)
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608
		)
		names = {row.name for row in visible}
		self.assertNotIn(other_trainee.name, names)

	def test_unassigned_manager_still_sees_own_trainer_assignment(self):
		# Review Focus: a Day-1 trainee with no assigned_sales_manager yet must not
		# vanish from everyone's view — their assigned_trainer must still see them.
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608
		)
		names = {row.name for row in visible}
		self.assertIn(self.trainee_no_manager_yet.name, names)

	def test_admin_sees_everything(self):
		condition = sales_trainee_query_conditions("Administrator")
		self.assertEqual(condition, "")
