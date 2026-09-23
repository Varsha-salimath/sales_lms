# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _

EXIT_STATUSES = ("Resigned", "Absconded", "Exited/Churned")


@frappe.whitelist()
def get_cohort_stats(cohort):
	_ensure_cohort_stats_access()
	rows = frappe.get_list("Sales Trainee", filters={"cohort": cohort}, fields=["training_status"], limit_page_length=0)
	total = len(rows)
	exits = sum(1 for r in rows if r.training_status in EXIT_STATUSES)
	active = sum(1 for r in rows if r.training_status == "In Training")
	cleared = sum(1 for r in rows if r.training_status == "Training Cleared")
	not_cleared = sum(1 for r in rows if r.training_status == "Training Not Cleared")
	return {"total": total, "active": active, "exits": exits, "cleared": cleared, "not_cleared": not_cleared}


@frappe.whitelist()
def list_missing_attendance(attendance_date, cohort=None):
	"""Names of In Training trainees with no Sales Trainee Attendance row for the date."""
	_ensure_cohort_stats_access()
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	active_trainees = frappe.get_list("Sales Trainee", filters=filters, pluck="name", limit_page_length=0)
	if not active_trainees:
		return []
	marked = set(
		frappe.get_list(
			"Sales Trainee Attendance",
			filters={"trainee": ["in", active_trainees], "attendance_date": attendance_date},
			pluck="trainee",
			limit_page_length=0,
		)
	)
	return [name for name in active_trainees if name not in marked]


def _ensure_cohort_stats_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team", "Sales Trainee Manager", "Sales Training Finance", "Sales Training Leadership"}):
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
