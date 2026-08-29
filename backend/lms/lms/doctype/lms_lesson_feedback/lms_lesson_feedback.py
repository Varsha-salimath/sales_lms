import frappe
from frappe import _
from frappe.model.document import Document


class LMSLessonFeedback(Document):
	def validate(self):
		self.validate_enrollment()

	def validate_enrollment(self):
		privileged = {"System Manager", "Moderator", "Course Creator"}
		if privileged.intersection(set(frappe.get_roles(self.member))):
			return

		course = frappe.db.get_value("Course Lesson", self.lesson, "course")
		if not course:
			return
		enrollment = frappe.db.exists(
			"LMS Enrollment", {"course": course, "member": self.member}
		)
		if not enrollment:
			frappe.throw(_("You must be enrolled in the course to submit feedback."))
