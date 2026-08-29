import frappe
from frappe import _
from frappe.model.document import Document


class LMSLearnerReview(Document):
	def validate(self):
		if self.mock_rating is not None and (self.mock_rating < 0 or self.mock_rating > 5):
			frappe.throw(_("Mock rating must be between 0 and 5."))

		existing = frappe.db.exists(
			"LMS Learner Review",
			{"batch": self.batch, "member": self.member, "name": ["!=", self.name]},
		)
		if existing:
			frappe.throw(_("A review record already exists for this learner in this batch."))
