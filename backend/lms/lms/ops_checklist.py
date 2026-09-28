# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime, add_months, date_diff, getdate

from lms.lms import access
from lms.lms.trainee_cohort_stats import list_missing_attendance
from lms.lms.trainee_dashboard import get_dashboard_summary
from lms.lms.trainee_scope import ORG_WIDE_TRAINEE_ROLES

PAYROLL_EXPORT_DAY = 25
SALES_TRAINING_ROLES = ORG_WIDE_TRAINEE_ROLES | {"Sales Trainee Manager"}


def _ensure_logged_in():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


@frappe.whitelist()
def get_ops_checklist_tour_state():
	_ensure_logged_in()
	skipped_on = frappe.db.get_value("Ops Checklist Tour State", frappe.session.user, "skipped_on")
	return {"skipped": bool(skipped_on), "skipped_on": skipped_on}


@frappe.whitelist()
def skip_ops_checklist_tour():
	_ensure_logged_in()
	if frappe.db.exists("Ops Checklist Tour State", frappe.session.user):
		frappe.db.set_value("Ops Checklist Tour State", frappe.session.user, "skipped_on", now_datetime())
	else:
		frappe.get_doc(
			{"doctype": "Ops Checklist Tour State", "user": frappe.session.user, "skipped_on": now_datetime()}
		).insert(ignore_permissions=True)
	return {"skipped": True}


def _safe_section(label, fn):
	"""Each checklist section is independent — one bad query must not blank the
	whole page for every other section (spec §4)."""
	try:
		return fn()
	except Exception:
		frappe.log_error(title=f"Ops Checklist: {label} section failed")
		return [{"key": f"error:{label}", "title": f"Couldn't load {label} — try reloading.", "action_route": None}]


@frappe.whitelist()
def get_ops_checklist():
	_ensure_ops_checklist_access()
	roles = set(frappe.get_roles())
	items = []

	org_wide_view = access.is_admin() or "Sales Training Team" in roles
	if org_wide_view:
		items += _safe_section("attendance", _team_attendance_items)
	elif "Sales Trainee Manager" in roles:
		items += _safe_section("attendance", lambda: _manager_attendance_items(frappe.session.user))

	if org_wide_view:
		items += _safe_section("payroll deadline", _payroll_deadline_item)

	if "Sales Training Finance" in roles:
		items += _safe_section("payroll cycles", _finance_items)

	summary = None
	if "Sales Training Leadership" in roles:
		try:
			summary = get_dashboard_summary()
		except Exception:
			frappe.log_error(title="Ops Checklist: leadership summary section failed")
			summary = None

	return {"items": items, "summary": summary}


def _ensure_ops_checklist_access():
	_ensure_logged_in()
	roles = set(frappe.get_roles())
	if not (access.is_admin() or roles & SALES_TRAINING_ROLES):
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


def _team_attendance_items():
	today = getdate()
	items = []
	for cohort_name in frappe.get_all("Sales Trainee Cohort", pluck="name"):
		missing = list_missing_attendance(str(today), cohort=cohort_name)
		if missing:
			items.append(
				{
					"key": f"attendance:{cohort_name}",
					"title": f"{len(missing)} trainee(s) in cohort {cohort_name} have no attendance marked for {today}",
					"action_route": {"name": "TraineeAttendance"},
				}
			)
	return items


def _manager_attendance_items(user):
	today = getdate()
	lines = [
		(row.member, row.manager)
		for row in frappe.get_all("LMS Reporting Line", filters={"status": "Active"}, fields=["member", "manager"])
	]
	visible_users = access.reporting_tree(user, lines) | {user}
	my_trainees = frappe.get_all(
		"Sales Trainee",
		filters={"training_status": "In Training", "assigned_sales_manager": ["in", list(visible_users)]},
		fields=["name", "cohort"],
	)
	items = []
	cohorts = {t.cohort for t in my_trainees if t.cohort}
	for cohort_name in cohorts:
		mine_in_cohort = {t.name for t in my_trainees if t.cohort == cohort_name}
		missing = set(list_missing_attendance(str(today), cohort=cohort_name)) & mine_in_cohort
		if missing:
			items.append(
				{
					"key": f"attendance:{cohort_name}",
					"title": f"{len(missing)} of your trainee(s) in cohort {cohort_name} have no attendance marked for {today}",
					"action_route": {"name": "TraineeAttendance"},
				}
			)
	return items


def _payroll_deadline_item(today=None):
	today = today or getdate()
	if today.day <= PAYROLL_EXPORT_DAY:
		next_deadline = today.replace(day=PAYROLL_EXPORT_DAY)
	else:
		next_deadline = add_months(today.replace(day=1), 1).replace(day=PAYROLL_EXPORT_DAY)
	days_left = date_diff(next_deadline, today)
	return [
		{
			"key": "payroll-deadline",
			"title": f"Vendor payroll data due {next_deadline} ({days_left} day(s) left) — confirm all open payroll cycles are ready to export",
			"action_route": {"name": "WeeklyPayrollCycle"},
		}
	]


def _finance_items():
	items = []
	open_cycles = frappe.get_all(
		"Weekly Payroll Cycle", filters={"status": ["!=", "Closed"]}, fields=["name", "status", "week_end"]
	)
	for cycle in open_cycles:
		items.append(
			{
				"key": f"cycle:{cycle.name}",
				"title": f'Payroll cycle {cycle.name} (week ending {cycle.week_end}) is still "{cycle.status}" — move it forward before month-end close',
				"action_route": {"name": "WeeklyPayrollCycle"},
			}
		)
	return items
