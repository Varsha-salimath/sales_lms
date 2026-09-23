# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log

AUDITED_FIELDS = ("training_status", "exit_status", "exit_date", "exit_reason")


class SalesTrainee(Document):
	def on_update(self):
		if self.flags.get("status_change_reason_handled"):
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		for field in AUDITED_FIELDS:
			old_value, new_value = previous.get(field), self.get(field)
			if old_value != new_value:
				write_audit_log(
					trainee=self.name,
					field_changed=field,
					old_value=old_value,
					new_value=new_value,
					reason="No reason provided (direct edit)",
				)

	@frappe.whitelist()
	def update_training_status(self, new_status, reason, exit_status=None, exit_date=None, exit_reason=None):
		"""The intended path for changing training_status/exit fields — always
		captures a real reason. A raw doc.save() from the desk still gets logged
		by on_update() above, just with a fallback reason instead of this one."""
		# run_doc_method only checks READ on load; enforce write (role + scope hook) here.
		self.check_permission("write")
		if not (reason or "").strip():
			frappe.throw(_("A reason is required to change training status."), frappe.MandatoryError)

		changes = [("training_status", self.training_status, new_status)]
		self.training_status = new_status
		if exit_status is not None and exit_status != self.exit_status:
			changes.append(("exit_status", self.exit_status, exit_status))
			self.exit_status = exit_status
		if exit_date is not None and str(exit_date) != str(self.exit_date or ""):
			changes.append(("exit_date", self.exit_date, exit_date))
			self.exit_date = exit_date
		if exit_reason is not None and exit_reason != self.exit_reason:
			changes.append(("exit_reason", self.exit_reason, exit_reason))
			self.exit_reason = exit_reason

		self.flags.status_change_reason_handled = True
		self.save(ignore_permissions=True)

		for field, old_value, new_value in changes:
			if old_value != new_value:
				write_audit_log(
					trainee=self.name, field_changed=field, old_value=old_value, new_value=new_value, reason=reason
				)
		return self
