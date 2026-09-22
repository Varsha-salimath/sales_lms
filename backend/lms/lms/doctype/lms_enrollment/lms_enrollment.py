# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import ceil, flt


class LMSEnrollment(Document):
	def before_insert(self):
		self.validate_duplicate_enrollment()
		self.validate_course_enrollment_eligibility()
		self.validate_owner()
		self.reset_completion_fields_on_insert()

	def validate(self):
		self.protect_completion_fields()

	def validate_owner(self):
		"""Makes the member as the owner of the document so that users can update their progress"""
		if self.owner != self.member:
			self.owner = self.member

	def reset_completion_fields_on_insert(self):
		"""Students cannot seed progress or feedback flags at enrollment time."""
		if is_admin() or getattr(self.flags, "allow_progress_update", False):
			return
		self.progress = 0
		self.feedback_completed = 0

	def protect_completion_fields(self):
		"""
		progress / feedback_completed are server-owned.
		UI read_only is not enough — LMS Student has write if_owner.
		Trusted servers set flags.allow_progress_update (save_progress) or use db.set_value.
		"""
		if is_admin():
			return

		# Non-admins may only enroll themselves
		if self.is_new() and self.member and self.member != frappe.session.user:
			if not getattr(self.flags, "ignore_permissions", False):
				frappe.throw(_("You can only enroll yourself."), frappe.PermissionError)

		if self.is_new():
			if not getattr(self.flags, "allow_progress_update", False):
				self.progress = 0
			if not getattr(self.flags, "allow_feedback_flag_update", False):
				self.feedback_completed = 0
			return

		prev = self.get_doc_before_save()
		if not prev:
			return

		if not getattr(self.flags, "allow_progress_update", False):
			if flt(self.progress) != flt(prev.progress):
				self.progress = prev.progress

		if not getattr(self.flags, "allow_feedback_flag_update", False):
			if int(self.feedback_completed or 0) != int(prev.feedback_completed or 0):
				self.feedback_completed = prev.feedback_completed

	def after_insert(self):
		from lms.lms.lesson_locking import initialize_enrollment_progress

		initialize_enrollment_progress(self.name, self.course, self.member)

	def on_update(self):
		update_program_progress(self.member)
		# Certificate is issued only after mandatory feedback submission

	def on_change(self):
		# Progress updates no longer auto-issue certificates
		pass

	def issue_certificate_if_eligible(self):
		from frappe.utils import flt
		from lms.lms.doctype.lms_certificate.lms_certificate import (
			issue_certificate_on_completion,
		)
		from lms.lms.doctype.lms_course_feedback.lms_course_feedback import (
			has_course_feedback,
		)
		from lms.lms.utils import get_course_progress

		progress = flt(get_course_progress(self.course, self.member) or 0)
		if progress >= 100 and has_course_feedback(self.course, self.member):
			try:
				issue_certificate_on_completion(self.course, self.member)
			except Exception:
				frappe.log_error(
					title="Auto certificate issue failed",
					message=frappe.get_traceback(),
				)

	def validate_duplicate_enrollment(self):
		existing_enrollment = frappe.db.exists(
			"LMS Enrollment",
			{
				"course": self.course,
				"member": self.member,
				"name": ["!=", self.name],
			},
		)

		if existing_enrollment and existing_enrollment != self.name:
			frappe.throw(_("Student is already enrolled in this course."))

	def validate_course_enrollment_eligibility(self):
		course_details = frappe.db.get_value(
			"LMS Course",
			self.course,
			["published", "disable_self_learning", "paid_course", "paid_certificate"],
			as_dict=True,
		)

		# A published course still belongs to a team. Without this check a learner could enroll
		# themselves in another team's course through the REST API and then see all of its content.
		from lms.lms.content_scope import can_access

		if not is_admin() and not can_access("LMS Course", self.course, self.member):
			frappe.throw(_("This course is not available to you."), frappe.PermissionError)

		if course_details.disable_self_learning and not is_admin():
			frappe.throw(
				_(
					"You cannot enroll in this course as self-learning is disabled. Please contact the Administrator."
				)
			)

		if self.enrollment_from_batch:
			if not frappe.db.exists(
				"Batch Course", {"parent": self.enrollment_from_batch, "course": self.course}
			):
				frappe.throw(_("This batch is not associated with this course."))

			if frappe.db.exists(
				"LMS Batch Enrollment", {"batch": self.enrollment_from_batch, "member": self.member}
			):
				return

		if not course_details.published and not is_admin():
			frappe.throw(_("You cannot enroll in an unpublished course."))

		if course_details.paid_course and not is_admin():
			payment = frappe.db.exists(
				"LMS Payment",
				{
					"payment_for_document_type": "LMS Course",
					"payment_for_document": self.course,
					"member": self.member,
					"payment_received": True,
				},
			)

			if not payment:
				frappe.throw(_("You need to complete the payment for this course before enrolling."))


def is_admin():
	roles = frappe.get_roles(frappe.session.user)
	admin_roles = ["System Manager", "Moderator", "Course Creator", "Batch Evaluator"]
	for role in admin_roles:
		if role in roles:
			return True
	return False


def update_program_progress(member):
	programs = frappe.get_all("LMS Program Member", {"member": member}, ["parent", "name"])

	for program in programs:
		total_progress = 0
		courses = frappe.get_all("LMS Program Course", {"parent": program.parent}, pluck="course")
		for course in courses:
			progress = frappe.db.get_value("LMS Enrollment", {"course": course, "member": member}, "progress")
			progress = progress or 0
			total_progress += progress

		average_progress = ceil(total_progress / len(courses))
		frappe.db.set_value("LMS Program Member", program.name, "progress", average_progress)
