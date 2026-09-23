# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from lms.lms import access

STATUS_KEYS = {
	"In Training": "in_training",
	"Resigned": "resigned",
	"Absconded": "absconded",
	"Exited/Churned": "exited_churned",
	"Training Cleared": "training_cleared",
	"Training Not Cleared": "training_not_cleared",
}


@frappe.whitelist()
def get_dashboard_summary(month=None, location=None, cohort=None):
	_ensure_dashboard_access()
	filters = {}
	if location:
		filters["location"] = location
	if cohort:
		filters["cohort"] = cohort
	if month:
		filters["date_of_joining"] = ["like", f"{month}%"]

	rows = frappe.get_all("Sales Trainee", filters=filters, fields=["training_status"])
	summary = dict.fromkeys(STATUS_KEYS.values(), 0)
	for row in rows:
		key = STATUS_KEYS.get(row.training_status)
		if key:
			summary[key] += 1
	summary["total"] = len(rows)
	summary["payroll_eligible"] = summary["training_cleared"]

	open_cycles = frappe.get_all("Weekly Payroll Cycle", filters={"status": ["!=", "Closed"]}, fields=["status"])
	summary["open_payroll_cycles"] = len(open_cycles)
	return summary


def _ensure_dashboard_access():
	"""Mirrors Task 14's frontend nav-visibility condition for the Trainee Dashboard
	link (frontend/src/utils/index.js): Admin/Super Admin tier, or the Sales Training
	Leadership role. get_dashboard_summary uses frappe.get_all, which bypasses
	permission_query_conditions/has_permission hooks, so this gate is the only thing
	standing between a bare @frappe.whitelist() and any authenticated user reading
	trainee headcounts."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view the trainee dashboard."), frappe.PermissionError)
	if access.is_admin() or "Sales Training Leadership" in frappe.get_roles():
		return
	frappe.throw(_("You are not permitted to view the trainee dashboard."), frappe.PermissionError)
