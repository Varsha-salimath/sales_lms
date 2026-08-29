import frappe
from frappe import _
from frappe.model.document import Document


class LMSRecording(Document):
	def validate(self):
		if not self.drive_file_id:
			frappe.throw(_("Drive File ID is required."))
