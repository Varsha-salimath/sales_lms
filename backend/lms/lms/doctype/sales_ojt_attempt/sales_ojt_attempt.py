import frappe
from frappe import _
from frappe.model.document import Document


class SalesOJTAttempt(Document):
	def before_insert(self):
		self._restrict_to_owner()

	def validate(self):
		self._restrict_to_owner()

	def _restrict_to_owner(self):
		user = frappe.session.user
		if user in ("Administrator",) or "System Manager" in frappe.get_roles():
			return
		if self.member and self.member != user:
			frappe.throw(_("You can only access your own OJT attempts."))
