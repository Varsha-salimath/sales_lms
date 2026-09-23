# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log


class SalesTraineeAttendance(Document):
	def validate(self):
		if not self.marked_by:
			self.marked_by = frappe.session.user

	@frappe.whitelist()
	def correct(self, new_status, reason=None):
		"""Change status after the fact, always audit-logged. Allowed even after the
		owning Weekly Payroll Cycle has closed — Finance reconciles from the audit
		trail rather than being blocked from ever fixing a mistake."""
		if not (reason or "").strip():
			frappe.throw(_("A reason is required to correct attendance."), frappe.MandatoryError)
		old_status = self.status
		if old_status == new_status:
			return self
		write_audit_log(
			trainee=self.trainee,
			field_changed=f"attendance:{self.name}",
			old_value=old_status,
			new_value=new_status,
			reason=reason,
		)
		self.status = new_status
		self.save(ignore_permissions=True)
		return self


def mark(trainee, attendance_date, status, source="Manual", marked_by=None):
	"""Upsert one attendance row for trainee+date. Never creates a duplicate for the
	same (trainee, attendance_date) pair — a second call for the same day updates
	the existing row instead."""
	attendance_date = getdate(attendance_date)
	existing = frappe.db.get_value(
		"Sales Trainee Attendance", {"trainee": trainee, "attendance_date": attendance_date}, "name"
	)
	if existing:
		doc = frappe.get_doc("Sales Trainee Attendance", existing)
		doc.status = status
		doc.source = source
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Sales Trainee Attendance",
				"trainee": trainee,
				"attendance_date": attendance_date,
				"status": status,
				"source": source,
				"marked_by": marked_by or frappe.session.user,
			}
		)
	doc.save(ignore_permissions=True)
	return doc
