# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms import access


class LMSMember(Document):
	def validate(self):
		primaries = [row for row in self.departments if row.is_primary]
		if len(primaries) > 1:
			frappe.throw(_("Only one department can be marked primary."))
		if self.departments and not primaries:
			self.departments[0].is_primary = 1

		for row in self.departments:
			if row.designation:
				designation_dept = frappe.db.get_value("LMS Designation", row.designation, "department")
				if designation_dept != row.department:
					frappe.throw(
						_("Row {0}: designation {1} belongs to {2}, not {3}.").format(
							row.idx, row.designation, designation_dept, row.department
						)
					)

		if self.is_new() and not self.access_role:
			self.access_role = self.default_access_role() or "User"

		enabled = frappe.db.get_value("User", self.user, "enabled")
		self.status = "Active" if enabled else "Inactive"

	def default_access_role(self):
		primary = next((row for row in self.departments if row.is_primary and row.designation), None)
		if primary:
			return frappe.db.get_value("LMS Designation", primary.designation, "default_access_role")

	def on_update(self):
		sync_frappe_roles(self.user, self.access_role)
		access.clear_cache()


def sync_frappe_roles(user, access_role):
	"""Make the user's LMS tier roles match their access role.

	Super Admins (System Manager / Administrator) are never touched, and only the four tier
	roles are managed; every other role on the user is left alone.
	"""
	if user == "Administrator":
		return
	current = set(frappe.get_roles(user))
	if "System Manager" in current:
		return

	wanted = set(access.ACCESS_ROLE_FRAPPE_ROLES.get(access_role, []))
	user_doc = frappe.get_doc("User", user)
	to_add = [role for role in wanted if role not in current and frappe.db.exists("Role", role)]
	to_remove = [role for role in access.TIER_ROLES if role in current and role not in wanted]
	if not to_add and not to_remove:
		return
	if to_remove:
		user_doc.remove_roles(*to_remove)
	if to_add:
		user_doc.add_roles(*to_add)
