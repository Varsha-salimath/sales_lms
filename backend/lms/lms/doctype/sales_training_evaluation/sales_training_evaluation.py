import frappe
from frappe import _
from frappe.model.document import Document


class SalesTrainingEvaluation(Document):
	def validate(self):
		user = frappe.session.user
		if user in ("Administrator",) or "System Manager" in frappe.get_roles():
			return
		if self.member and self.member != user:
			frappe.throw(_("You can only access your own training evaluation."))
