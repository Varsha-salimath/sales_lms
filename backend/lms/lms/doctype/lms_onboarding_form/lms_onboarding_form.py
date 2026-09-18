# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LMSOnboardingForm(Document):
	"""'Hello ILians': the joining form a Sales new joiner fills before CRT 1 opens."""

	def validate(self):
		self.employee_name = " ".join(p for p in (self.first_name, self.last_name) if p)
		if self.edtech_experience == "No":
			self.last_edtech_company = "No EdTech Experience"
		elif not self.last_edtech_company:
			frappe.throw(frappe._("Enter your last EdTech company."))
