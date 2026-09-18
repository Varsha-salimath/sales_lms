# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from lms.lms import access


class LMSReportingLine(Document):
	def validate(self):
		if self.member == self.manager:
			frappe.throw(_("A person cannot report to themselves."))

		if self.status == "Ended" and not self.is_new():
			previous = self.get_doc_before_save()
			if previous and previous.status == "Ended":
				frappe.throw(_("This reporting line has ended and can no longer be changed."))

		if self.status == "Active":
			self.validate_no_duplicate()
			self.validate_no_cycle()

	def validate_no_duplicate(self):
		duplicate = frappe.db.exists(
			"LMS Reporting Line",
			{
				"member": self.member,
				"manager": self.manager,
				"line_type": self.line_type,
				"status": "Active",
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("{0} already reports to {1} as {2} ({3}).").format(
					self.member, self.manager, self.line_type, duplicate
				)
			)

	def validate_no_cycle(self):
		lines = [
			(row.member, row.manager)
			for row in frappe.get_all(
				"LMS Reporting Line",
				filters={"status": "Active", "name": ["!=", self.name]},
				fields=["member", "manager"],
			)
		]
		if self.member in access.managers_above(self.manager, lines):
			frappe.throw(_("{0} is above {1} already; this line would create a loop.").format(self.member, self.manager))

	def on_change(self):
		access.clear_cache()

	@frappe.whitelist()
	def end_line(self, reason: str | None = None):
		"""End the line. The old manager immediately loses all view of this person."""
		if not access.can_manage_member(self.member) and not access.is_admin():
			frappe.throw(_("Not permitted to end this reporting line."), frappe.PermissionError)
		end_reporting_line(self, reason)


def end_reporting_line(doc, reason=None, ended_by=None):
	if doc.status == "Ended":
		return
	doc.status = "Ended"
	doc.to_date = max(getdate(nowdate()), getdate(doc.from_date))
	doc.ended_by = ended_by or frappe.session.user
	doc.end_reason = reason or ""
	doc.flags.ignore_permissions = True
	doc.save()


def end_lines_for_user(user, reason):
	"""End every active line where `user` is the member or the manager."""
	for name in frappe.get_all(
		"LMS Reporting Line",
		filters={"status": "Active"},
		or_filters={"member": user, "manager": user},
		pluck="name",
	):
		end_reporting_line(frappe.get_doc("LMS Reporting Line", name), reason)
