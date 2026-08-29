import frappe
from frappe import _
from frappe.model.document import Document


class LMSDailyActivity(Document):
	def validate(self):
		existing = frappe.db.exists(
			"LMS Daily Activity",
			{
				"user": self.user,
				"date": self.date,
				"module": self.module,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				_("A daily activity record already exists for this user, date, and module.")
			)
