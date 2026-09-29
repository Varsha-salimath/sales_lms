# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# Closing a cycle stamps finance_validated_by, so only someone actually in Finance
# (or a System Manager) may take that final step.
CLOSE_ROLES = {"Sales Training Finance", "System Manager"}

STATUS_SEQUENCE = [
	"Preparing",
	"Ready to Share",
	"Shared with Vendor",
	"Awaiting Invoice",
	"Finance Validation",
	"Closed",
]


class WeeklyPayrollCycle(Document):
	@frappe.whitelist()
	def advance_status(self, new_status):
		# run_doc_method only checks READ on load, and we save with ignore_permissions,
		# so write access has to be enforced here.
		self.check_permission("write")
		if new_status == "Closed" and set(frappe.get_roles()).isdisjoint(CLOSE_ROLES):
			frappe.throw(_("Only Sales Training Finance can close a payroll cycle."), frappe.PermissionError)
		current_index = STATUS_SEQUENCE.index(self.status)
		try:
			target_index = STATUS_SEQUENCE.index(new_status)
		except ValueError:
			frappe.throw(_("{0} is not a valid payroll cycle status.").format(new_status))
		if target_index != current_index + 1:
			frappe.throw(
				_("Cannot move from {0} to {1} — cycles advance one step at a time.").format(
					self.status, new_status
				)
			)
		self.status = new_status
		if new_status == "Shared with Vendor":
			self.shared_on = now_datetime()
		if new_status == "Closed":
			self.finance_validated_by = frappe.session.user
			self.finance_validated_on = now_datetime()
		self.save(ignore_permissions=True)
		return self
