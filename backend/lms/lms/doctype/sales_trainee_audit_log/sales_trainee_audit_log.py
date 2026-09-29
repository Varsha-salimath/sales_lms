# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SalesTraineeAuditLog(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Audit log entries cannot be edited after creation."))
		if not (self.reason or "").strip():
			frappe.throw(_("A reason is required for every audit log entry."), frappe.MandatoryError)


def write_audit_log(trainee, field_changed, old_value, new_value, reason, changed_by=None):
	"""Create one immutable audit entry. Raises frappe.MandatoryError if reason is blank."""
	log = frappe.get_doc(
		{
			"doctype": "Sales Trainee Audit Log",
			"trainee": trainee,
			"field_changed": field_changed,
			"old_value": old_value,
			"new_value": new_value,
			"changed_by": changed_by or frappe.session.user,
			"reason": reason,
		}
	)
	log.insert(ignore_permissions=True)
	return log
