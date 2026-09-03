"""Sequential lesson progression — unlock lessons in strict order."""

import frappe
from frappe import _

from lms.lms.utils import (
	can_modify_course,
	get_lesson_index,
	has_course_instructor_role,
	has_moderator_role,
	is_instructor,
)


def should_enforce_sequential_locking(course: str, member: str = None) -> bool:
	"""Instructors and moderators can access any lesson."""
	if not member:
		member = frappe.session.user
	if member == "Guest":
		return False
	roles = set(frappe.get_roles(member))
	if roles & {"System Manager", "Administrator", "Moderator", "Course Creator"}:
		return False
	if has_moderator_role(member) or has_course_instructor_role(member):
		return False
	if can_modify_course(course) or is_instructor(course):
		return False
	return bool(frappe.db.exists("LMS Enrollment", {"course": course, "member": member}))


def get_ordered_lessons(course: str) -> list:
	"""Return lesson document names in chapter/lesson order."""
	ordered = []
	chapters = frappe.get_all(
		"Chapter Reference", {"parent": course}, ["chapter", "idx"], order_by="idx"
	)
	for chapter in chapters:
		lessons = frappe.get_all(
			"Lesson Reference",
			{"parent": chapter.chapter},
			["lesson"],
			order_by="idx",
		)
		for row in lessons:
			ordered.append(row.lesson)
	return ordered


def get_first_lesson(course: str):
	lessons = get_ordered_lessons(course)
	return lessons[0] if lessons else None


def get_completed_lessons(course: str, member: str = None) -> set:
	if not member:
		member = frappe.session.user
	rows = frappe.get_all(
		"LMS Course Progress",
		{"course": course, "member": member, "status": "Complete"},
		pluck="lesson",
	)
	return set(rows or [])


def is_lesson_unlocked(course: str, lesson: str, member: str = None) -> bool:
	if not should_enforce_sequential_locking(course, member):
		return True

	ordered = get_ordered_lessons(course)
	if lesson not in ordered:
		return False

	completed = get_completed_lessons(course, member)
	if lesson in completed:
		return True

	idx = ordered.index(lesson)
	if idx == 0:
		return True

	for previous in ordered[:idx]:
		if previous not in completed:
			return False
	return True


def get_current_lesson(course: str, member: str = None) -> str | None:
	"""First incomplete lesson in order, or last lesson if all complete."""
	if not member:
		member = frappe.session.user

	ordered = get_ordered_lessons(course)
	if not ordered:
		return None

	completed = get_completed_lessons(course, member)
	for lesson in ordered:
		if lesson not in completed:
			return lesson
	return ordered[-1]


def get_lesson_route_numbers(lesson_name: str) -> dict:
	"""Return chapterNumber and lessonNumber for the Vue router."""
	index = get_lesson_index(lesson_name)
	if not index:
		return {"chapter_number": 1, "lesson_number": 1}
	parts = index.replace(".", "-").split("-")
	return {
		"chapter_number": int(parts[0]),
		"lesson_number": int(parts[1]),
	}


def enrich_lesson_lock_status(course: str, lessons: list, member: str = None) -> list:
	"""Add is_locked and is_current flags to lesson dicts in the outline."""
	if not member:
		member = frappe.session.user

	enforce = should_enforce_sequential_locking(course, member)
	current = get_current_lesson(course, member) if enforce else None

	if not enforce:
		current = None

	for lesson in lessons:
		lesson["is_locked"] = (
			enforce and not is_lesson_unlocked(course, lesson.get("name"), member)
		)
		lesson["is_current"] = bool(current and lesson.get("name") == current)

	return lessons


def get_locked_lesson_redirect(course: str, member: str = None) -> dict:
	current = get_current_lesson(course, member)
	if not current:
		return {}
	numbers = get_lesson_route_numbers(current)
	return {
		"lesson_locked": 1,
		"current_lesson": current,
		"current_lesson_index": get_lesson_index(current),
		"chapter_number": numbers["chapter_number"],
		"lesson_number": numbers["lesson_number"],
	}


def initialize_enrollment_progress(enrollment_name: str, course: str, member: str):
	"""On enrolment, set current lesson to the first lesson in the course."""
	first = get_first_lesson(course)
	if first:
		frappe.db.set_value(
			"LMS Enrollment",
			enrollment_name,
			"current_lesson",
			first,
			update_modified=False,
		)
