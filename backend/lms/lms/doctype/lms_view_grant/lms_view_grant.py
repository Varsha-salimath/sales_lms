# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms import access

SCOPE_FIELD = {"Department": "department", "Designation": "designation", "Batch": "batch"}


class LMSViewGrant(Document):
	def validate(self):
		field = SCOPE_FIELD.get(self.scope_type)
		if field and not self.get(field):
			frappe.throw(_("Pick the {0} this grant covers.").format(_(self.scope_type)))
		# Keep only the field that belongs to the chosen scope.
		for other in SCOPE_FIELD.values():
			if other != field:
				self.set(other, None)
		if self.scope_type == "Everyone" and not access.is_super_admin():
			frappe.throw(_("Only a Super Admin can grant access to everyone."), frappe.PermissionError)

	def on_change(self):
		access.clear_cache()
