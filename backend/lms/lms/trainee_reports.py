# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import base64
import io

import frappe
import openpyxl
from frappe import _


@frappe.whitelist()
def export_active_trainees_csv(cohort=None, location=None):
	"""Active Trainee Report (spec §9) as a base64-encoded XLSX."""
	_ensure_report_access()
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	if location:
		filters["location"] = location
	rows = frappe.get_all(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "personal_email", "location", "cohort", "date_of_joining", "employee_dummy_vendor_code"],
		order_by="date_of_joining asc",
	)
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = "Active Trainees"
	sheet.append(["Trainee Name", "Personal Email", "Location", "Cohort", "Date of Joining", "Employee/Dummy/Vendor Code"])
	for row in rows:
		sheet.append(
			[row.trainee_name, row.personal_email, row.location, row.cohort, str(row.date_of_joining or ""), row.employee_dummy_vendor_code]
		)
	buffer = io.BytesIO()
	workbook.save(buffer)
	return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _ensure_report_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team", "Sales Trainee Manager", "Sales Training Finance", "Sales Training Leadership"}):
		frappe.throw(_("You are not permitted to export this report."), frappe.PermissionError)
