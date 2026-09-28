# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import base64
import io

import frappe
import openpyxl
from frappe import _


def _to_xlsx(sheet_title, headers, rows):
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = sheet_title
	sheet.append(headers)
	for row in rows:
		sheet.append(row)
	buffer = io.BytesIO()
	workbook.save(buffer)
	return base64.b64encode(buffer.getvalue()).decode("utf-8")


@frappe.whitelist()
def export_active_trainees_csv(cohort=None, location=None):
	"""Active Trainee Report (spec §9)."""
	_ensure_report_access()
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	if location:
		filters["location"] = location
	rows = frappe.get_list(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "personal_email", "location", "cohort", "date_of_joining", "employee_dummy_vendor_code"],
		order_by="date_of_joining asc",
		limit_page_length=0,
	)
	return _to_xlsx(
		"Active Trainees",
		["Trainee Name", "Personal Email", "Location", "Cohort", "Date of Joining", "Employee/Dummy/Vendor Code"],
		[[r.trainee_name, r.personal_email, r.location, r.cohort, str(r.date_of_joining or ""), r.employee_dummy_vendor_code] for r in rows],
	)


@frappe.whitelist()
def export_weekly_attendance_payroll_report(week_start, week_end, cohort=None):
	_ensure_report_access()
	filters = {"attendance_date": ["between", [week_start, week_end]]}
	if cohort:
		trainee_names = frappe.get_list("Sales Trainee", filters={"cohort": cohort}, pluck="name", limit_page_length=0)
		filters["trainee"] = ["in", trainee_names]
	rows = frappe.get_list(
		"Sales Trainee Attendance",
		filters=filters,
		fields=["trainee", "attendance_date", "status", "source"],
		order_by="attendance_date asc",
		limit_page_length=0,
	)
	return _to_xlsx(
		"Weekly Attendance",
		["Trainee", "Date", "Status", "Source"],
		[[r.trainee, str(r.attendance_date), r.status, r.source] for r in rows],
	)


@frappe.whitelist()
def export_vendor_payroll_input(cycle_name):
	_ensure_report_access()
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	return _to_xlsx(
		"Vendor Payroll Input",
		["Trainee", "Salary", "Working Days", "Payable Days", "Adjustment Note"],
		[[r.trainee, r.salary, r.working_days, r.payable_days, r.joining_or_exit_adjustment_note] for r in cycle.payroll_inputs],
	)


@frappe.whitelist()
def export_exit_churn_report(month=None):
	_ensure_report_access()
	filters = {"training_status": ["in", ["Resigned", "Absconded", "Exited/Churned"]]}
	rows = frappe.get_list(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "training_status", "exit_date", "exit_reason", "cohort"],
		order_by="exit_date desc",
		limit_page_length=0,
	)
	if month:
		rows = [r for r in rows if r.exit_date and str(r.exit_date).startswith(month)]
	return _to_xlsx(
		"Exit and Churn",
		["Trainee Name", "Exit Status", "Exit Date", "Exit Reason", "Cohort"],
		[[r.trainee_name, r.training_status, str(r.exit_date or ""), r.exit_reason, r.cohort] for r in rows],
	)


@frappe.whitelist()
def export_training_outcome_report(cohort=None):
	_ensure_report_access()
	filters = {}
	if cohort:
		filters["cohort"] = cohort
	rows = frappe.get_list(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "training_status", "location", "cohort"],
		order_by="cohort asc",
		limit_page_length=0,
	)
	return _to_xlsx(
		"Training Outcomes",
		["Trainee Name", "Training Status", "Location", "Cohort"],
		[[r.trainee_name, r.training_status, r.location, r.cohort] for r in rows],
	)


@frappe.whitelist()
def export_location_cohort_report():
	_ensure_report_access()
	from lms.lms.trainee_cohort_stats import get_cohort_stats

	cohorts = frappe.get_all("Sales Trainee Cohort", fields=["name", "location", "start_date"])
	rows = []
	for c in cohorts:
		stats = get_cohort_stats(c.name)
		rows.append([c.name, c.location, str(c.start_date or ""), stats["total"], stats["active"], stats["exits"]])
	return _to_xlsx(
		"Location and Cohort",
		["Cohort", "Location", "Start Date", "Total", "Active", "Exits"],
		rows,
	)


@frappe.whitelist()
def export_finance_reconciliation_report(cycle_name):
	_ensure_report_access()
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	captured_total = sum((row.salary or 0) * (row.payable_days or 0) / max(row.working_days or 1, 1) for row in cycle.payroll_inputs)
	# "Captured Estimate" is a display-only cross-check for Finance to eyeball against the
	# vendor's number — it is not a pro-rata calculation the system relies on anywhere else
	# (spec §2 still holds: capture only, no computed payout).
	return _to_xlsx(
		"Finance Reconciliation",
		["Cycle", "Week Start", "Week End", "Status", "Captured Estimate", "Vendor Invoice Amount"],
		[[cycle.name, str(cycle.week_start), str(cycle.week_end), cycle.status, round(captured_total, 2), cycle.vendor_invoice_amount]],
	)


def _ensure_report_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team", "Sales Trainee Manager", "Sales Training Finance", "Sales Training Leadership"}):
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
