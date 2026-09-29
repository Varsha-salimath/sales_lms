# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe

from lms.lms import access

# Roles that see every trainee org-wide. Sales Training Team is here because it runs
# bulk onboarding (sales_trainee_import.py), which never sets assigned_trainer /
# assigned_sales_manager, and owns CRT-week fallback marking for all trainees.
ORG_WIDE_TRAINEE_ROLES = {"Sales Training Team", "Sales Training Finance", "Sales Training Leadership"}


def _active_reporting_lines():
	return [
		(row.member, row.manager)
		for row in frappe.get_all("LMS Reporting Line", filters={"status": "Active"}, fields=["member", "manager"])
	]


def _sees_everything(user):
	if access.is_admin(user):
		return True
	roles = set(frappe.get_roles(user))
	return bool(roles & ORG_WIDE_TRAINEE_ROLES)


def sales_trainee_query_conditions(user=None):
	"""Scope Sales Trainee / Sales Trainee Attendance visibility to a manager's own
	reporting tree, keyed by assigned_sales_manager / assigned_trainer rather than
	a Link->User on the trainee itself (the trainee has none). A trainee with no
	assigned_sales_manager yet still shows up via assigned_trainer, so a fresh
	Day-1 onboard is never invisible to everyone."""
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	escaped = ", ".join(frappe.db.escape(u) for u in visible_users)
	return (
		f"(`tabSales Trainee`.assigned_sales_manager in ({escaped}) "
		f"or `tabSales Trainee`.assigned_trainer in ({escaped}))"
	)


def sales_trainee_attendance_query_conditions(user=None):
	"""Same scoping as sales_trainee_query_conditions, joined through the trainee."""
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	escaped = ", ".join(frappe.db.escape(u) for u in visible_users)
	return (
		f"`tabSales Trainee Attendance`.trainee in ("
		f"select name from `tabSales Trainee` where assigned_sales_manager in ({escaped}) "
		f"or assigned_trainer in ({escaped}))"
	)


def sales_trainee_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _sees_everything(user):
		return True
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	trainee_doc = doc if doc.doctype == "Sales Trainee" else frappe.get_cached_doc("Sales Trainee", doc.trainee)
	return trainee_doc.assigned_sales_manager in visible_users or trainee_doc.assigned_trainer in visible_users
