# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.realtime import get_website_room
from frappe.utils import flt
from frappe.utils.telemetry import capture

from lms.lms.utils import get_course_progress, is_demo_course, recalculate_course_progress, sanitize_editorjs

from ...md import find_macros


class CourseLesson(Document):
	def after_insert(self):
		self.validate_progress_recalculation()

	def after_delete(self):
		self.validate_progress_recalculation()

	def validate(self):
		self.content = sanitize_editorjs(self.content)
		self.instructor_content = sanitize_editorjs(self.instructor_content)

	def on_update(self):
		self.validate_quiz_id()

	def validate_progress_recalculation(self):
		if not self.course or not self.chapter:
			return

		enrollments = frappe.db.get_all(
			"LMS Enrollment",
			filters={"course": self.course},
			fields=["name", "member"],
		)
		if not len(enrollments):
			return

		frappe.enqueue(method=self.recalculate_progress, queue="long", is_async=True, enrollments=enrollments)

	def recalculate_progress(self, enrollments):
		for enrollment in enrollments:
			recalculate_course_progress(self.course, enrollment.member)

	def validate_quiz_id(self):
		if self.quiz_id and not frappe.db.exists("LMS Quiz", self.quiz_id):
			frappe.throw(_("Invalid Quiz ID"))

		if self.content:
			self.save_lesson_details_in_quiz(self.content)

		if self.instructor_content:
			self.save_lesson_details_in_quiz(self.instructor_content)

	def save_lesson_details_in_quiz(self, content):
		content = json.loads(self.content)
		for block in content.get("blocks"):
			if block.get("type") == "quiz":
				quiz = block.get("data").get("quiz")
				if not frappe.db.exists("LMS Quiz", quiz):
					frappe.throw(_("Invalid Quiz ID in content"))
				frappe.db.set_value(
					"LMS Quiz",
					quiz,
					{
						"course": self.course,
						"lesson": self.name,
					},
				)


@frappe.whitelist()
def save_progress(lesson: str, course: str, scorm_details: dict = None):
	"""
	Note: Pass the argument scorm_details as a dict if it is SCORM related save_progress

	SCORM packages assert completion via cmi.completion_status / success_status (honor system
	inherent to SCORM). Certificate eligibility still requires server-recalculated progress
	plus an LMS Course Feedback document — not enrollment flags alone.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to continue."), frappe.PermissionError)

	membership = frappe.db.exists("LMS Enrollment", {"course": course, "member": frappe.session.user})
	if not membership:
		return 0

	from lms.lms.lesson_locking import is_lesson_unlocked, should_enforce_sequential_locking

	if should_enforce_sequential_locking(course) and not is_lesson_unlocked(
		course, lesson, frappe.session.user
	):
		frappe.throw(_("This lesson is locked."), frappe.PermissionError)

	frappe.db.set_value("LMS Enrollment", membership, "current_lesson", lesson, update_modified=False)
	progress_already_exists = frappe.db.exists(
		"LMS Course Progress", {"lesson": lesson, "member": frappe.session.user}
	)
	lesson_already_completed = frappe.db.exists(
		"LMS Course Progress",
		{"lesson": lesson, "member": frappe.session.user, "status": "Complete"},
	)

	quiz_completed = get_quiz_progress(lesson)
	assignment_completed = get_assignment_progress(lesson)

	if scorm_details:
		if isinstance(scorm_details, str):
			try:
				scorm_details = json.loads(scorm_details)
			except (TypeError, ValueError, json.JSONDecodeError):
				frappe.throw(_("Invalid SCORM progress payload."))
		scorm_details = frappe._dict(**scorm_details)
		# Normalize completion flag (packages send bool / "true" / 1 / "completed")
		raw_complete = scorm_details.get("is_complete")
		if isinstance(raw_complete, str):
			scorm_details.is_complete = raw_complete.strip().lower() in (
				"1",
				"true",
				"yes",
				"completed",
				"passed",
			)
		else:
			scorm_details.is_complete = bool(raw_complete)
		# Clamp score if present
		if scorm_details.get("scorm_score") is not None:
			try:
				scorm_details.scorm_score = flt(min(100, max(0, float(scorm_details.scorm_score))), 3)
			except (TypeError, ValueError):
				scorm_details.scorm_score = None

	if not progress_already_exists and quiz_completed and assignment_completed and not scorm_details:
		frappe.get_doc(
			{
				"doctype": "LMS Course Progress",
				"lesson": lesson,
				"status": "Complete",
				"member": frappe.session.user,
			}
		).save(ignore_permissions=True)
	elif scorm_details and not lesson_already_completed and not progress_already_exists:
		# Create new SCORM progress
		progress_doc = {
			"doctype": "LMS Course Progress",
			"lesson": lesson,
			"status": "Complete" if scorm_details.is_complete else "Partially Complete",
			"member": frappe.session.user,
			"scorm_content": "" if scorm_details.is_complete else scorm_details.get("scorm_content"),
		}
		if scorm_details.get("scorm_score") is not None:
			progress_doc["scorm_score"] = scorm_details.scorm_score
		if scorm_details.get("scorm_total_time") is not None:
			progress_doc["scorm_total_time"] = scorm_details.scorm_total_time
		if scorm_details.is_complete:
			progress_doc["scorm_progress"] = 100
		elif scorm_details.get("progress_measure") is not None:
			try:
				measure = float(scorm_details.progress_measure)
				if measure <= 1:
					measure = measure * 100
				progress_doc["scorm_progress"] = flt(min(100, max(0, measure)), 3)
			except (TypeError, ValueError):
				pass
		frappe.get_doc(progress_doc).save(ignore_permissions=True)
	elif scorm_details and not lesson_already_completed and progress_already_exists:
		# Update Existing SCORM Progress
		values = {
			"lesson": lesson,
			"status": "Complete" if scorm_details.is_complete else "Partially Complete",
			"member": frappe.session.user,
			"scorm_content": "" if scorm_details.is_complete else scorm_details.get("scorm_content"),
		}
		if scorm_details.get("scorm_score") is not None:
			values["scorm_score"] = scorm_details.scorm_score
		if scorm_details.get("scorm_total_time") is not None:
			values["scorm_total_time"] = scorm_details.scorm_total_time
		if scorm_details.is_complete:
			values["scorm_progress"] = 100
		elif scorm_details.get("progress_measure") is not None:
			try:
				measure = float(scorm_details.progress_measure)
				if measure <= 1:
					measure = measure * 100
				values["scorm_progress"] = flt(min(100, max(0, measure)), 3)
			except (TypeError, ValueError):
				pass
		frappe.db.set_value(
			"LMS Course Progress",
			progress_already_exists,
			values,
		)
	elif scorm_details and lesson_already_completed and progress_already_exists:
		# Keep score/time/progress fresh after completion
		values = {}
		if scorm_details.get("scorm_score") is not None:
			values["scorm_score"] = scorm_details.scorm_score
		if scorm_details.get("scorm_total_time") is not None:
			values["scorm_total_time"] = scorm_details.scorm_total_time
		if scorm_details.is_complete:
			values["scorm_progress"] = 100
		elif scorm_details.get("progress_measure") is not None:
			try:
				measure = float(scorm_details.progress_measure)
				if measure <= 1:
					measure = measure * 100
				values["scorm_progress"] = flt(min(100, max(0, measure)), 3)
			except (TypeError, ValueError):
				pass
		if values:
			frappe.db.set_value("LMS Course Progress", progress_already_exists, values)

	if (not progress_already_exists and quiz_completed and assignment_completed and not scorm_details) or (
		scorm_details and scorm_details.is_complete and not lesson_already_completed
	):
		next_lesson = get_next_lesson(course, lesson)
		if next_lesson:
			frappe.db.set_value(
				"LMS Enrollment",
				membership,
				"current_lesson",
				next_lesson,
				update_modified=False,
			)
	progress = get_course_progress(course)

	# SCORM mid-lesson progress_measure (0..1) contributes to enrollment %
	if scorm_details and not scorm_details.is_complete:
		measure = scorm_details.get("progress_measure")
		if measure is not None:
			from lms.lms.utils import get_lessons as _get_lessons

			lesson_count = _get_lessons(course, get_details=False) or 1
			completed_lessons = frappe.db.count(
				"LMS Course Progress",
				{"course": course, "member": frappe.session.user, "status": "Complete"},
			)
			try:
				measure = float(measure)
			except (TypeError, ValueError):
				measure = 0
			if measure > 1:
				measure = measure / 100.0
			measure = max(0.0, min(1.0, measure))
			if not lesson_already_completed:
				progress = flt(((completed_lessons + measure) / lesson_count) * 100, 3)

	if not is_demo_course(course):
		capture("course_progress", "lms")

	# Had to get doc, as on_change doesn't trigger when you use set_value. The trigger is necessary for badge to get assigned.
	enrollment = frappe.get_doc("LMS Enrollment", membership)
	enrollment.progress = progress
	enrollment.flags.ignore_version = True
	enrollment.flags.allow_progress_update = True
	enrollment.save()
	enrollment.run_method("on_change")

	frappe.publish_realtime(
		event="update_lesson_progress",
		room=get_website_room(),
		message={"course": course, "lesson": lesson, "progress": progress},
		after_commit=True,
	)

	return progress


def get_next_lesson(course: str, lesson: str):
	lesson_reference = frappe.db.get_value(
		"Lesson Reference", {"lesson": lesson}, ["idx", "parent"], as_dict=1
	)
	if not lesson_reference:
		return None

	total_lessons = frappe.db.count("Lesson Reference", {"parent": lesson_reference.parent})
	if lesson_reference.idx < total_lessons:
		return frappe.db.get_value(
			"Lesson Reference", {"parent": lesson_reference.parent, "idx": lesson_reference.idx + 1}, "lesson"
		)

	total_chapters = frappe.db.count("Chapter Reference", {"parent": course})
	current_chapter_reference = frappe.db.get_value(
		"Chapter Reference", {"parent": course, "chapter": lesson_reference.parent}, ["idx"], as_dict=1
	)

	if current_chapter_reference.idx >= total_chapters:
		return None

	next_chapter = frappe.db.get_value(
		"Chapter Reference", {"parent": course, "idx": current_chapter_reference.idx + 1}, "chapter"
	)
	return frappe.db.get_value("Lesson Reference", {"parent": next_chapter, "idx": 1}, "lesson")


def get_quiz_progress(lesson):
	lesson_details = frappe.db.get_value("Course Lesson", lesson, ["body", "content"], as_dict=1)
	quizzes = []

	if lesson_details.content:
		content = json.loads(lesson_details.content)

		for block in content.get("blocks"):
			if block.get("type") == "quiz":
				quizzes.append(block.get("data").get("quiz"))
			if block.get("type") == "upload":
				quizzes_in_video = block.get("data").get("quizzes")
				if quizzes_in_video and len(quizzes_in_video) > 0:
					for row in quizzes_in_video:
						quizzes.append(row.get("quiz"))

	elif lesson_details.body:
		macros = find_macros(lesson_details.body)
		quizzes = [value for name, value in macros if name == "Quiz"]

	for quiz in quizzes:
		passing_percentage = frappe.db.get_value("LMS Quiz", quiz, "passing_percentage")
		if not frappe.db.exists(
			"LMS Quiz Submission",
			{
				"quiz": quiz,
				"member": frappe.session.user,
				"percentage": [">=", passing_percentage],
			},
		):
			return False
	return True


def get_assignment_progress(lesson):
	lesson_details = frappe.db.get_value("Course Lesson", lesson, ["body", "content"], as_dict=1)
	assignments = []

	if lesson_details.content:
		content = json.loads(lesson_details.content)

		for block in content.get("blocks"):
			if block.get("type") == "assignment":
				assignments.append(block.get("data").get("assignment"))

	elif lesson_details.body:
		macros = find_macros(lesson_details.body)
		assignments = [value for name, value in macros if name == "Assignment"]

	for assignment in assignments:
		if not frappe.db.exists(
			"LMS Assignment Submission",
			{"assignment": assignment, "member": frappe.session.user},
		):
			return False
	return True
