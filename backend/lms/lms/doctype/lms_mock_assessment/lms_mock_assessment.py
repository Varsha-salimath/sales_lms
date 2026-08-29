import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from lms.lms.mock_assessment import (
	default_evaluation_sections,
	parse_evaluation_sections,
	serialize_evaluation_sections,
)


class LMSMockAssessment(Document):
	def validate(self):
		if not self.title or not str(self.title).strip():
			frappe.throw(_("Mock title is required."))

		duplicate = frappe.db.exists(
			"LMS Mock Assessment",
			{
				"batch": self.batch,
				"member": self.member,
				"title": self.title.strip(),
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("A mock titled \"{0}\" already exists for this learner. Use a different title.").format(
					self.title.strip()
				)
			)

		overall = frappe.utils.cint(self.overall_rating or 0)
		if overall and (overall < 1 or overall > 5):
			frappe.throw(_("Overall rating must be between 1 and 5."))

		if self.attendance_percent is not None:
			attendance = flt(self.attendance_percent)
			if attendance < 0 or attendance > 100:
				frappe.throw(_("Attendance percentage must be between 0 and 100."))

		if self.assessment_score_percent is not None:
			score = flt(self.assessment_score_percent)
			if score < 0 or score > 100:
				frappe.throw(_("Assessment score must be between 0 and 100."))

		sections = parse_evaluation_sections(self.evaluation_sections)
		for section in sections:
			rating = frappe.utils.cint(section.get("rating") or 0)
			if rating and (rating < 1 or rating > 5):
				frappe.throw(
					_("Section rating for {0} must be between 1 and 5.").format(
						section.get("label") or section.get("key")
					)
				)

		if isinstance(self.evaluation_sections, list):
			self.evaluation_sections = serialize_evaluation_sections(sections)
		elif not self.evaluation_sections:
			self.evaluation_sections = serialize_evaluation_sections(default_evaluation_sections())

	def before_insert(self):
		if not self.evaluation_sections:
			self.evaluation_sections = serialize_evaluation_sections(default_evaluation_sections())

	def publish(self):
		self.status = "Published"
		self.published_on = now_datetime()
		self.save(ignore_permissions=True)

	def unpublish(self):
		self.status = "Draft"
		self.published_on = None
		self.save(ignore_permissions=True)
