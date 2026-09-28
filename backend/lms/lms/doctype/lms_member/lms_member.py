# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms import access

ACCESS_ROLE_RANK = {"User": 0, "Instructor": 1, "Manager": 2, "Admin": 3}
VALID_ACCESS_ROLES = set(ACCESS_ROLE_RANK)


def normalize_access_roles_list(roles) -> list[str]:
	if roles is None:
		return ["User"]
	if isinstance(roles, str):
		roles = roles.strip()
		if not roles:
			return ["User"]
		try:
			parsed = json.loads(roles)
			roles = parsed if isinstance(parsed, list) else [roles]
		except json.JSONDecodeError:
			roles = [roles]
	if not isinstance(roles, (list, tuple)):
		roles = [roles]
	staff = []
	for role in roles:
		if role in VALID_ACCESS_ROLES and role != "User" and role not in staff:
			staff.append(role)
	if not staff:
		return ["User"]
	return staff


def highest_access_role(roles) -> str:
	normalized = normalize_access_roles_list(roles)
	return max(normalized, key=lambda r: ACCESS_ROLE_RANK.get(r, 0))


def member_has_access_role(member_doc_or_roles, role: str) -> bool:
	if isinstance(member_doc_or_roles, (list, tuple, str)):
		roles = normalize_access_roles_list(member_doc_or_roles)
	else:
		roles = normalize_access_roles_list(
			getattr(member_doc_or_roles, "access_roles", None)
			or [getattr(member_doc_or_roles, "access_role", None) or "User"]
		)
	return role in roles


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

		if self.is_new() and not self.access_role and not self.access_roles:
			self.access_role = self.default_access_role() or "User"

		roles = normalize_access_roles_list(self.access_roles or [self.access_role or "User"])
		self.access_roles = roles
		self.access_role = highest_access_role(roles)

		enabled = frappe.db.get_value("User", self.user, "enabled")
		self.status = "Active" if enabled else "Inactive"

	def default_access_role(self):
		primary = next((row for row in self.departments if row.is_primary and row.designation), None)
		if primary:
			return frappe.db.get_value("LMS Designation", primary.designation, "default_access_role")

	def on_update(self):
		sync_frappe_roles_for_access_roles(self.user, self.access_roles or [self.access_role or "User"])
		access.clear_cache()


def sync_frappe_roles(user, access_role):
	"""Back-compat: single access role."""
	sync_frappe_roles_for_access_roles(user, [access_role or "User"])


def sync_frappe_roles_for_access_roles(user, access_roles):
	"""Make the user's LMS tier Frappe roles match their access roles (union of all selected)."""
	if user == "Administrator":
		return
	current = set(frappe.get_roles(user))
	if "System Manager" in current:
		return

	roles = normalize_access_roles_list(access_roles)
	wanted = set()
	for role in roles:
		wanted |= set(access.ACCESS_ROLE_FRAPPE_ROLES.get(role, []))

	user_doc = frappe.get_doc("User", user)
	to_add = [role for role in wanted if role not in current and frappe.db.exists("Role", role)]
	to_remove = [role for role in access.TIER_ROLES if role in current and role not in wanted]
	if not to_add and not to_remove:
		return
	if to_remove:
		user_doc.remove_roles(*to_remove)
	if to_add:
		user_doc.add_roles(*to_add)
