# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Org lifecycle: departures, the unassigned queue, and seeding departments."""

import frappe
from frappe import _

from lms.lms import access
from lms.lms.doctype.lms_reporting_line.lms_reporting_line import end_lines_for_user

DEFAULT_DEPARTMENTS = [  # (name, parent, description)
	("HR", None, ""),
	("Genius", None, ""),
	("Retail Sales", None, "B2C retail sales"),
	("Retail Sales Training", None, "Trains the retail (B2C) sales team: CRT, OJT, refreshers"),
	("SCA Sales", None, ""),
	("CS", None, "Customer success"),
	("AcadOps", None, "Academic operations"),
	("Delivery", None, ""),
]


def on_user_update(doc, method=None):
	"""A deactivated account ends all its reporting lines and view grants.

	Their reports drop into the unassigned queue for an admin to re-home. Training data is
	kept; only the departed person's access goes.
	"""
	if not frappe.db.exists("DocType", "LMS Member"):
		return
	previous = doc.get_doc_before_save()
	was_enabled = previous.enabled if previous else doc.enabled
	if frappe.db.exists("LMS Member", doc.name):
		frappe.db.set_value("LMS Member", doc.name, "status", "Active" if doc.enabled else "Inactive")
	if was_enabled and not doc.enabled:
		end_lines_for_user(doc.name, _("Account deactivated"))
		for grant in frappe.get_all("LMS View Grant", filters={"user": doc.name, "is_active": 1}, pluck="name"):
			frappe.db.set_value("LMS View Grant", grant, "is_active", 0)
	access.clear_cache()


@frappe.whitelist()
def get_unassigned_members():
	"""Active members with no active reporting line — the re-homing queue for admins."""
	if not access.is_admin():
		frappe.throw(_("Only admins can see the unassigned queue."), frappe.PermissionError)
	assigned = set(frappe.get_all("LMS Reporting Line", filters={"status": "Active"}, pluck="member"))
	members = frappe.get_all(
		"LMS Member",
		filters={"status": "Active"},
		fields=["name", "full_name", "access_role"],
		order_by="full_name asc",
	)
	return [m for m in members if m.name not in assigned]


def seed_departments():
	"""Create the starting departments once (after_migrate). Admins edit them freely afterwards."""
	if not frappe.db.exists("DocType", "LMS Department"):
		return
	for name, parent, description in DEFAULT_DEPARTMENTS:
		if not frappe.db.exists("LMS Department", name):
			frappe.get_doc(
				{
					"doctype": "LMS Department",
					"department_name": name,
					"parent_department": parent,
					"description": description,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)
