# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate


def compute_payable_days(trainee, week_start, week_end):
	"""Count Present days for trainee in [week_start, week_end], never counting past
	exit_date if the trainee exited mid-week."""
	week_start, week_end = getdate(week_start), getdate(week_end)
	exit_date = frappe.db.get_value("Sales Trainee", trainee, "exit_date")
	effective_end = min(week_end, getdate(exit_date)) if exit_date else week_end
	if effective_end < week_start:
		return 0
	return frappe.db.count(
		"Sales Trainee Attendance",
		{
			"trainee": trainee,
			"attendance_date": ["between", [week_start, effective_end]],
			"status": "Present",
		},
	)


def _ensure_payroll_prep_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to prepare payroll inputs."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team", "Sales Training Finance"}):
		frappe.throw(_("You are not permitted to prepare payroll inputs."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def prepare_weekly_inputs(cycle_name):
	"""Populate payroll_inputs on a Weekly Payroll Cycle from attendance + current
	trainee salary. Capture-only: does not compute a pro-rata amount (spec §2)."""
	_ensure_payroll_prep_access()
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	filters = {"training_status": "In Training"}
	if cycle.cohort:
		filters["cohort"] = cycle.cohort
	trainees = frappe.get_all("Sales Trainee", filters=filters, fields=["name", "salary", "date_of_joining"])
	cycle.payroll_inputs = []
	for t in trainees:
		effective_start = max(getdate(cycle.week_start), getdate(t.date_of_joining))
		working_days = max((getdate(cycle.week_end) - effective_start).days + 1, 0)
		payable_days = compute_payable_days(t.name, cycle.week_start, cycle.week_end)
		cycle.append(
			"payroll_inputs",
			{"trainee": t.name, "salary": t.salary, "working_days": working_days, "payable_days": payable_days},
		)
	cycle.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "trainee_count": len(trainees)}
