import frappe
from frappe import _
from frappe.model.document import Document


class LMSRecordingAssignment(Document):
	def validate(self):
		if not self.assigned_by:
			self.assigned_by = frappe.session.user

		if frappe.db.exists(
			"LMS Recording Assignment",
			{"recording": self.recording, "member": self.member, "name": ["!=", self.name]},
		):
			frappe.throw(_("This student is already assigned to the recording."))
