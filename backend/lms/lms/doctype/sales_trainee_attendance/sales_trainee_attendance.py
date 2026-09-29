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
		# run_doc_method only checks READ on load; enforce write (role + scope hook) here.
		self.check_permission("write")
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
		# A corrected row must be treated as Manual going forward, otherwise the next
		# Zoom sync for the same trainee+date silently reverts the correction (N1).
		self.source = "Manual"
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


def _ensure_attendance_mark_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to mark attendance."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team", "Sales Trainee Manager"}):
		frappe.throw(_("You are not permitted to mark attendance."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def mark_attendance(trainee, attendance_date, status, reason=None):
	"""Manual marking from the portal. A first mark for trainee+date creates the row.
	A re-mark of an existing row with a different status is a correction, so it is
	routed server-side through correct() (write permission, mandatory reason,
	audit log) instead of mark()'s silent overwrite. Deciding here rather than in
	the client keeps the audit guarantee independent of which call the UI picks."""
	_ensure_attendance_mark_access()
	existing = frappe.db.get_value(
		"Sales Trainee Attendance", {"trainee": trainee, "attendance_date": getdate(attendance_date)}, "name"
	)
	if existing:
		doc = frappe.get_doc("Sales Trainee Attendance", existing)
		if doc.status == status:
			doc.check_permission("write")
			return doc.as_dict()
		return doc.correct(status, reason=reason).as_dict()
	# mark() saves with ignore_permissions, so apply the reporting-tree scope here:
	# a Sales Trainee Manager may only mark trainees in their own tree.
	frappe.has_permission(
		"Sales Trainee Attendance",
		"create",
		doc=frappe.get_doc({"doctype": "Sales Trainee Attendance", "trainee": trainee}),
		throw=True,
	)
	return mark(trainee, attendance_date, status, source="Manual").as_dict()
