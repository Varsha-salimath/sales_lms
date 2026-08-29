# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime


class LMSCourseFeedback(Document):
	def validate(self):
		self.bind_learner_identity()
		self.validate_unique_feedback()
		self.validate_completion()

	def bind_learner_identity(self):
		"""Students cannot submit feedback as another learner via REST/Desk."""
		user = frappe.session.user
		if not user or user == "Guest":
			frappe.throw(_("Please login to submit feedback."), frappe.PermissionError)

		roles = set(frappe.get_roles(user))
		is_staff = bool(
			roles.intersection(
				{"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}
			)
		)
		if not is_staff:
			self.learner = user

		if not self.learner:
			frappe.throw(_("Learner is required."))

		# Always derive email/name from User — never trust client overrides for identity
		user_info = frappe.db.get_value(
			"User", self.learner, ["full_name", "email"], as_dict=True
		) or {}
		self.learner_email = user_info.get("email") or self.learner
		self.learner_name = user_info.get("full_name") or self.learner

	def validate_unique_feedback(self):
		existing = frappe.db.exists(
			"LMS Course Feedback",
			{
				"learner": self.learner,
				"course": self.course,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(_("You have already submitted feedback for this course."))

	def validate_completion(self):
		from lms.lms.utils import get_course_progress

		progress = flt(get_course_progress(self.course, self.learner) or 0)
		if progress < 100:
			frappe.throw(_("Feedback can be submitted only after completing the course."))

	def after_insert(self):
		self.mark_feedback_completed()
		self.issue_certificate()

	def mark_feedback_completed(self):
		enrollment_name = frappe.db.exists(
			"LMS Enrollment", {"course": self.course, "member": self.learner}
		)
		if not enrollment_name:
			return
		# db.set_value bypasses Document.validate — intentional server-owned denormalized flag
		frappe.db.set_value(
			"LMS Enrollment",
			enrollment_name,
			{
				"feedback_completed": 1,
			},
			update_modified=False,
		)

	def issue_certificate(self):
		from lms.lms.doctype.lms_certificate.lms_certificate import (
			issue_certificate_on_completion,
		)

		try:
			issue_certificate_on_completion(self.course, self.learner)
		except Exception:
			frappe.log_error(
				title="Certificate after feedback failed",
				message=frappe.get_traceback(),
			)


def has_course_feedback(course: str, member: str | None = None) -> bool:
	member = member or frappe.session.user
	if not course or not member or member == "Guest":
		return False
	return bool(
		frappe.db.exists("LMS Course Feedback", {"course": course, "learner": member})
	)


def is_feedback_completed(course: str, member: str | None = None) -> bool:
	"""True only when an LMS Course Feedback document exists (not enrollment flag alone)."""
	return has_course_feedback(course, member)


@frappe.whitelist()
def get_feedback_status(course: str):
	"""Return completion + feedback + certificate status for the current user."""
	from lms.lms.utils import get_course_progress

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login to continue."), frappe.PermissionError)

	enrollment = frappe.db.get_value(
		"LMS Enrollment",
		{"course": course, "member": user},
		["name", "progress", "feedback_completed", "certificate"],
		as_dict=True,
	)
	if not enrollment:
		frappe.throw(_("You are not enrolled in this course."))

	# Prefer recalculated progress over forgeable enrollment.progress
	progress = flt(get_course_progress(course, user) or 0)
	feedback_done = has_course_feedback(course, user)
	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": user, "course": course},
		["name", "template"],
		as_dict=True,
	)
	course_doc = frappe.db.get_value(
		"LMS Course",
		course,
		["title", "enable_certification"],
		as_dict=True,
	) or {}

	user_info = frappe.db.get_value(
		"User", user, ["full_name", "email"], as_dict=True
	) or {}

	return {
		"course": course,
		"course_title": course_doc.get("title") or course,
		"enable_certification": int(course_doc.get("enable_certification") or 0),
		"progress": progress,
		"course_completed": progress >= 100,
		"feedback_completed": feedback_done,
		"certificate": certificate,
		"can_generate_certificate": progress >= 100
		and feedback_done
		and bool(course_doc.get("enable_certification")),
		"learner_name": user_info.get("full_name") or user,
		"learner_email": user_info.get("email") or user,
	}


@frappe.whitelist()
def submit_course_feedback(course: str, feedback: dict | str):
	"""Submit mandatory course feedback and unlock certificate generation."""
	import json

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login to continue."), frappe.PermissionError)

	if isinstance(feedback, str):
		feedback = json.loads(feedback)

	status = get_feedback_status(course)
	if not status.get("course_completed"):
		frappe.throw(_("Complete the course before submitting feedback."))
	if status.get("feedback_completed"):
		# Already submitted — return existing certificate status
		return {
			"feedback": frappe.db.get_value(
				"LMS Course Feedback",
				{"course": course, "learner": user},
				"name",
			),
			"certificate": status.get("certificate"),
			"already_submitted": 1,
		}

	required = [
		"school_name",
		"overall_rating",
		"relevance",
		"understanding",
		"valuable_topic",
		"confidence",
		"followability",
		"trainer_rating",
		"takeaway",
		"future_training",
		"recommendation",
	]
	missing = [f for f in required if not str(feedback.get(f) or "").strip()]
	if missing:
		frappe.throw(_("Please fill all required feedback fields: {0}").format(", ".join(missing)))

	doc = frappe.get_doc(
		{
			"doctype": "LMS Course Feedback",
			"learner": user,
			"learner_email": status["learner_email"],
			"course": course,
			"school_name": feedback.get("school_name"),
			"overall_rating": str(feedback.get("overall_rating")),
			"relevance": feedback.get("relevance"),
			"understanding": feedback.get("understanding"),
			"valuable_topic": feedback.get("valuable_topic"),
			"confidence": feedback.get("confidence"),
			"followability": feedback.get("followability"),
			"trainer_rating": str(feedback.get("trainer_rating")),
			"takeaway": feedback.get("takeaway"),
			"future_training": feedback.get("future_training"),
			"recommendation": feedback.get("recommendation"),
			"suggestions": feedback.get("suggestions") or "",
			"submitted_on": now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": user, "course": course},
		["name", "template"],
		as_dict=True,
	)
	return {
		"feedback": doc.name,
		"certificate": certificate,
		"already_submitted": 0,
	}


@frappe.whitelist()
def get_feedback_analytics(
	course: str | None = None,
	start: int | str = 0,
	page_length: int | str = 50,
):
	"""Aggregate feedback metrics and paginated full feedback rows for admin dashboard."""
	roles = set(frappe.get_roles())
	if not roles.intersection({"System Manager", "Moderator", "Course Creator"}):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	filters = {}
	if course:
		filters["course"] = course

	feedback_fields = [
		"name",
		"learner_name",
		"learner_email",
		"course",
		"course_title",
		"school_name",
		"overall_rating",
		"trainer_rating",
		"relevance",
		"understanding",
		"valuable_topic",
		"confidence",
		"followability",
		"future_training",
		"recommendation",
		"takeaway",
		"suggestions",
		"submitted_on",
	]

	# Load up to 2000 rows for aggregates + client/server paging of the list
	rows = frappe.get_all(
		"LMS Course Feedback",
		filters=filters,
		fields=feedback_fields,
		order_by="submitted_on desc",
		limit_page_length=2000,
	)

	total = len(rows)
	avg_overall = 0.0
	avg_trainer = 0.0
	topic_counts = {}
	recommend_positive = 0
	future_yes = 0
	relevance_counts = {}
	confidence_counts = {}

	for row in rows:
		try:
			avg_overall += float(row.overall_rating or 0)
		except (TypeError, ValueError):
			pass
		try:
			avg_trainer += float(row.trainer_rating or 0)
		except (TypeError, ValueError):
			pass
		topic = row.valuable_topic or "Other"
		topic_counts[topic] = topic_counts.get(topic, 0) + 1
		if row.recommendation in ("Definitely", "Probably"):
			recommend_positive += 1
		if row.future_training == "Yes":
			future_yes += 1
		if row.relevance:
			relevance_counts[row.relevance] = relevance_counts.get(row.relevance, 0) + 1
		if row.confidence:
			confidence_counts[row.confidence] = confidence_counts.get(row.confidence, 0) + 1

	top_topic = None
	if topic_counts:
		top_topic = max(topic_counts.items(), key=lambda x: x[1])[0]

	start = max(cint(start), 0)
	page_length = cint(page_length) or 50
	if page_length < 1:
		page_length = 50
	if page_length > 500:
		page_length = 500

	page_rows = rows[start : start + page_length]

	return {
		"total_responses": total,
		"average_rating": round(avg_overall / total, 2) if total else 0,
		"average_trainer_rating": round(avg_trainer / total, 2) if total else 0,
		"top_valuable_topic": top_topic,
		"recommendation_percent": round((recommend_positive / total) * 100, 1) if total else 0,
		"future_training_percent": round((future_yes / total) * 100, 1) if total else 0,
		"topic_breakdown": topic_counts,
		"relevance_breakdown": relevance_counts,
		"confidence_breakdown": confidence_counts,
		"feedback": rows,
		"recent_feedback": page_rows,
		"start": start,
		"page_length": page_length,
		"has_more": start + page_length < total,
	}
