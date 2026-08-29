import frappe
from frappe import _
from frappe.model.document import Document


class LMSCourseAssessmentVisibility(Document):
	def validate(self):
		if not frappe.db.exists(
			"LMS Assessment",
			{"name": self.course_assessment, "parent": self.course, "parenttype": "LMS Course"},
		):
			frappe.throw(_("Course assessment does not belong to this course."))

		if not frappe.db.exists("Batch Course", {"parent": self.batch, "course": self.course}):
			frappe.throw(_("This batch is not linked to the course."))
