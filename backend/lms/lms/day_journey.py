# Copyright (c) 2026, Infinity Learn and contributors
# For license information, please see license.txt

"""Day-by-day journeys for any course.

A course with "Day-by-day journey" on treats each chapter as a Day: Day N opens when Day N-1 is
complete, sessions unlock in order, and — with "End each day with a voice viva" — a day is only
complete once its viva is passed. Sales CRT is simply the first course set up this way; its home
screen, evaluation and OJT live in sales_journey.py and build on these states.

Days are addressed as /courses/<course>/days/<n>-<title-slug>; only the leading number matters,
so links survive a renamed day.
"""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.utils import cint

CRT_COURSE = "sales-crt"

# Default names for the Sales CRT days (applied once to chapters still called "CRT N").
CRT_DAY_TITLES = {
	1: "Welcome to Infinity Learn",
	2: "CBSE Foundation & Math Champ",
	3: "Test Prep: JEE & NEET",
	4: "LeadSquared & your leads",
	5: "Mock calls & demo",
}


def slugify(text: str) -> str:
	return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:60]


def day_slug(day: int, title: str) -> str:
	slug = slugify(clean_title(day, title))
	return f"{day}-{slug}" if slug else str(day)


def clean_title(day: int, title: str) -> str:
	"""Chapter title without a legacy 'CRT N' / 'Day N' prefix."""
	return re.sub(rf"^\s*(CRT|Day)\s*{day}\s*[:·\-–]?\s*", "", title or "", flags=re.I).strip()


def parse_day(value) -> int:
	match = re.match(r"\s*(\d+)", str(value or ""))
	return cint(match.group(1)) if match else 0


def is_day_journey(course: str) -> bool:
	return bool(frappe.db.get_value("LMS Course", course, "day_journey"))


def viva_on_for(course: str) -> bool:
	from lms.lms import sales_viva

	return sales_viva.is_required(course)


def progression_applies(course: str, member: str) -> bool:
	"""True when `member` goes day by day on this course (learners, or anyone on a learners-only course)."""
	from lms.lms.lesson_locking import should_enforce_sequential_locking

	return should_enforce_sequential_locking(course, member)


def day_states(member: str, course: str) -> list[dict]:
	"""One row per day (chapter) with its state for `member`."""
	from lms.lms import sales_viva
	from lms.lms.utils import get_course_outline

	gated = progression_applies(course, member)
	outline = get_course_outline(course, progress=True) or []
	chapters = sorted(outline, key=lambda c: cint(c.get("idx")))
	prev_complete = True
	if course == CRT_COURSE:
		# Sales CRT: Day 1 opens only after the Hello ILians joining form is in.
		from lms.lms.hello_ilians import is_required as hello_ilians_required

		prev_complete = not gated or not hello_ilians_required(member)
	viva_on = viva_on_for(course)
	gate_viva = viva_on and gated
	passed = sales_viva.passed_days(member, course) if viva_on else set()
	days = []
	for chapter in chapters:
		idx = cint(chapter.get("idx"))
		lessons = chapter.get("lessons") or []
		total = len(lessons)
		done = sum(1 for les in lessons if les.get("is_complete") or les.get("progress") == "Complete")
		if total == 0:
			state = "locked" if gated and not prev_complete else "empty"
			progress = 0
		elif gated and not prev_complete:
			state = "locked"
			progress = 0
		elif done >= total and gate_viva and idx not in passed:
			state = "viva_pending"
			progress = 95
		elif done >= total:
			state = "completed"
			progress = 100
		elif done > 0:
			state = "in_progress"
			progress = round((done / total) * 100)
		else:
			state = "available"
			progress = 0
		current = next((les for les in lessons if not (les.get("is_complete") or les.get("progress") == "Complete")), None)
		if not current and lessons:
			current = lessons[-1]
		title = clean_title(idx, chapter.get("title")) or _("Day {0}").format(idx)
		if gate_viva and state == "viva_pending":
			viva = sales_viva.day_viva_state(member, course, idx)
		else:
			viva = {"required": gate_viva, "passed": idx in passed, "can_try": bool(viva_on and not gated)}
		days.append(
			{
				"day": idx,
				"crt_number": idx,  # older Sales CRT screens still read this
				"title": title,
				"slug": day_slug(idx, title),
				"chapter": chapter.get("name"),
				"state": state,
				"progress": progress,
				"lessons_total": total,
				"lessons_done": done,
				"viva": viva,
				"current_lesson": {"name": current.get("name"), "title": current.get("title"), "number": current.get("number")}
				if current
				else None,
				"lessons": [
					{
						"name": les.get("name"),
						"title": les.get("title"),
						"number": les.get("number"),
						"complete": bool(les.get("is_complete") or les.get("progress") == "Complete"),
						"locked": bool(les.get("is_locked")) if gated else False,
					}
					for les in lessons
				],
			}
		)
		prev_complete = state == "completed" or state == "empty"
	return days


def _ensure_member(course: str, member: str):
	from lms.lms.content_scope import can_access

	if not can_access("LMS Course", course, member):
		frappe.throw(_("You don't have access to this course."), frappe.PermissionError)
	if course == CRT_COURSE:
		from lms.lms.sales_journey import _ensure_enrolled

		_ensure_enrolled(member)


@frappe.whitelist()
def get_course_journey(course: str):
	"""All days of a day-by-day course, for its journey page."""
	member = frappe.session.user
	if member == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	_ensure_member(course, member)
	info = frappe.db.get_value("LMS Course", course, ["name", "title", "short_introduction", "day_journey", "day_viva"], as_dict=True)
	if not info:
		frappe.throw(_("Course not found."))
	days = day_states(member, course)
	return {
		"course": info.name,
		"title": info.title,
		"description": info.short_introduction,
		"day_journey": bool(info.day_journey),
		"viva": viva_on_for(course),
		"enrolled": bool(frappe.db.exists("LMS Enrollment", {"course": course, "member": member})),
		"gated": progression_applies(course, member),
		"days": days,
		"progress": round(sum(d["progress"] for d in days) / max(1, len(days)), 1),
	}


@frappe.whitelist()
def get_day_detail(course: str, day):
	member = frappe.session.user
	if member == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	_ensure_member(course, member)
	number = parse_day(day)
	days = day_states(member, course)
	row = next((d for d in days if d["day"] == number), None)
	if not row:
		frappe.throw(_("Day {0} was not found.").format(number))
	sessions = []
	if course == CRT_COURSE and frappe.db.exists("DocType", "Sales CRT Session"):
		sessions = frappe.get_all(
			"Sales CRT Session",
			filters={"course": course, "day_number": number},
			fields=["session_key", "topic", "time_label", "stakeholder", "description", "session_type", "lesson", "day_label"],
			order_by="session_index asc",
		)
	next_step = None
	if number == len(days):
		next_step = "evaluation" if course == CRT_COURSE else "journey"
	return {
		"day": row,
		"crt": row,  # older Sales CRT screen
		"journey": days,
		"sessions": sessions,
		"course": course,
		"course_title": frappe.db.get_value("LMS Course", course, "title"),
		"next_step": next_step,
	}


def setup_crt_journey():
	"""after_migrate: Sales CRT is a day-by-day course with a viva, and its days have real names."""
	if not frappe.db.exists("LMS Course", CRT_COURSE) or not frappe.db.has_column("LMS Course", "day_journey"):
		return
	# Seed the flags once. After that they belong to whoever edits the course: a deploy must not
	# switch the journey or the viva back on for a course where an admin turned them off.
	if not frappe.db.get_default("crt_journey_seeded"):
		frappe.db.set_value("LMS Course", CRT_COURSE, {"day_journey": 1, "day_viva": 1}, update_modified=False)
		frappe.db.set_default("crt_journey_seeded", "1")
	for ref in frappe.get_all("Chapter Reference", {"parent": CRT_COURSE}, ["chapter", "idx"]):
		title = frappe.db.get_value("Course Chapter", ref.chapter, "title") or ""
		if re.fullmatch(rf"\s*CRT\s*{cint(ref.idx)}\s*", title) and cint(ref.idx) in CRT_DAY_TITLES:
			frappe.db.set_value("Course Chapter", ref.chapter, "title", CRT_DAY_TITLES[cint(ref.idx)], update_modified=False)
