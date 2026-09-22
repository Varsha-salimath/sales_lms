# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Sales CRT Excel importer + schedule APIs.

Curriculum source of truth is the CRT schedule workbook (not frontend constants).
Importer is idempotent: re-import updates the Sales CRT course in place.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, time
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, escape_html, nowdate

from lms.lms.utils import (
	can_modify_course,
	has_course_instructor_role,
	has_moderator_role,
)
from lms.lms.ppt_content import build_lesson_content, to_curriculum

COURSE_SLUG = "sales-crt"
DEMO_LEARNER_EMAIL = "learner@sales.localhost"
COURSE_TITLE = "Sales CRT - Classroom Readiness Training"
REQUIRED_COLUMNS = ["day", "time", "stakeholder", "topic", "description", "content link"]
BUNDLED_EXCEL = os.path.join(os.path.dirname(__file__), "data", "CRT-Schedule.xlsx")
IMAGE_DATA_PATH = "/opt/sales-lms/data/CRT-Schedule.xlsx"

DAY_RE = re.compile(r"day\s*(\d+)", re.I)
DAY_START_RE = re.compile(r"^day\s*\d+\s*start$", re.I)
DURATION_RE = re.compile(
	r"\(\s*(\d+(?:\.\d+)?)\s*(hr|hrs|hour|hours|h)\s*(?:(\d+)\s*(min|mins|minute|minutes|m))?\s*\)",
	re.I,
)
DURATION_MIN_RE = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*(min|mins|minute|minutes|m)\s*\)", re.I)
URL_RE = re.compile(r"(https?://[^\s]+|(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s]*)?)", re.I)


def _ensure_can_import():
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if not (
		has_moderator_role()
		or has_course_instructor_role()
		or "System Manager" in frappe.get_roles()
	):
		frappe.throw(_("You do not have permission to import the CRT schedule."), frappe.PermissionError)


def _norm_header(value) -> str:
	return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _cell_text(value) -> str:
	if value is None:
		return ""
	if isinstance(value, datetime):
		return value.strftime("%I:%M:%S %p").lstrip("0")
	if isinstance(value, time):
		return value.strftime("%I:%M:%S %p").lstrip("0")
	return str(value).strip()


def _looks_like_url(text: str) -> bool:
	t = (text or "").strip()
	if not t or " " in t:
		return False
	if t.startswith(("http://", "https://")):
		return True
	if "." in t and not t.endswith("."):
		host = t.split("/")[0]
		return bool(re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", host, re.I))
	return False


def _normalize_url(raw: str) -> str:
	url = (raw or "").strip().rstrip(".,);")
	if not url:
		return ""
	if url.startswith(("http://", "https://")):
		return url
	return f"https://{url}"


def parse_content_links(raw) -> list[dict]:
	text = _cell_text(raw)
	if not text:
		return []
	links = []
	for chunk in re.split(r"[\n\r]+", text):
		chunk = chunk.strip()
		if not chunk:
			continue
		match = URL_RE.search(chunk)
		if match:
			url = _normalize_url(match.group(1).rstrip(".,);"))
			label = chunk[: match.start()].strip(" -:–—").strip() or urlparse(url).netloc or "Link"
			links.append({"label": label[:140], "url": url})
			continue
		if _looks_like_url(chunk):
			url = _normalize_url(chunk)
			links.append({"label": urlparse(url).netloc or "Link", "url": url})
			continue
		# Non-URL note (e.g. "Q&A Round", "PPT to be created.")
		links.append({"label": chunk[:140], "url": ""})
	# Child table URL is required — drop notes without URLs from the table,
	# keep them as description footnotes instead.
	return [row for row in links if row.get("url")]


def parse_duration_minutes(time_label: str) -> int | None:
	text = _cell_text(time_label)
	if not text:
		return None
	match = DURATION_RE.search(text)
	if match:
		hours = float(match.group(1))
		mins = int(match.group(3) or 0)
		return int(round(hours * 60 + mins))
	match = DURATION_MIN_RE.search(text)
	if match:
		return int(round(float(match.group(1))))
	range_match = re.search(
		r"(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\s*[-–—to]+\s*(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)",
		text,
		re.I,
	)
	if range_match:
		try:
			fmt_candidates = ["%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"]
			start = end = None
			for fmt in fmt_candidates:
				if start is None:
					try:
						start = datetime.strptime(range_match.group(1).strip().upper(), fmt)
					except ValueError:
						pass
				if end is None:
					try:
						end = datetime.strptime(range_match.group(2).strip().upper(), fmt)
					except ValueError:
						pass
			if start and end:
				delta = (end - start).seconds // 60
				return delta if delta > 0 else None
		except Exception:
			return None
	return None


def classify_session_type(time_label: str, topic: str) -> str:
	blob = f"{time_label} {topic}".lower()
	if "lunch" in blob:
		return "lunch"
	if "break" in blob:
		return "break"
	if "assessment" in blob or "quiz" in blob:
		return "assessment"
	if "calling" in blob or "audit" in blob:
		return "calling"
	if any(word in blob for word in ("activity", "mock", "recording", "certificate", "live class")):
		return "activity"
	return "session"


def _parse_day_number(value) -> int | None:
	text = _cell_text(value)
	if not text or DAY_START_RE.match(text):
		return None
	match = DAY_RE.search(text)
	if match:
		return int(match.group(1))
	return None


def _is_banner_row(day, time_label, topic, stakeholder, description) -> bool:
	day_text = _cell_text(day)
	if DAY_START_RE.match(day_text) and not _cell_text(time_label) and not _cell_text(topic):
		return True
	return False


def _is_empty_row(values: dict) -> bool:
	return not any(_cell_text(values.get(k)) for k in ("day", "time", "stakeholder", "topic", "description", "content link"))


def _session_title(time_label: str, topic: str, session_type: str, idx: int) -> str:
	topic = _cell_text(topic)
	if topic:
		first = topic.split("\n")[0].strip()
		return first[:140]
	if session_type == "lunch":
		return "Lunch Break"
	if session_type == "break":
		return "Break"
	return f"Session {idx}"


def _lesson_content_json(session: dict) -> str:
	return build_lesson_content(session)


def _html_description(text: str) -> str:
	if not text:
		return ""
	escaped = escape_html(text).replace("\n", "<br>")
	return f"<p>{escaped}</p>"


def parse_crt_workbook(path: str) -> dict:
	try:
		from openpyxl import load_workbook
	except ImportError:
		frappe.throw(_("openpyxl is required to import the CRT Excel schedule."))

	if not path or not os.path.exists(path):
		frappe.throw(_("Excel file not found at {0}").format(path))

	wb = load_workbook(path, data_only=True)
	sheet_name = None
	for name in wb.sheetnames:
		if "crt" in name.lower() and "schedule" in name.lower():
			sheet_name = name
			break
	if not sheet_name:
		sheet_name = wb.sheetnames[0]

	ws = wb[sheet_name]
	header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
	if not header_row:
		frappe.throw(_("Sheet {0} has no header row.").format(sheet_name))

	headers = [_norm_header(h) for h in header_row]
	missing = [col for col in REQUIRED_COLUMNS if col not in headers]
	if missing:
		frappe.throw(
			_("Sheet {0} is missing required columns: {1}. Found: {2}").format(
				sheet_name, ", ".join(missing), ", ".join([h for h in headers if h])
			)
		)

	col_index = {name: headers.index(name) for name in REQUIRED_COLUMNS}
	sessions = []
	errors = []
	current_day = None
	current_day_label = None
	session_index = 0

	for excel_row, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
		if not row:
			continue
		values = {
			key: (row[col_index[key]] if col_index[key] < len(row) else None) for key in REQUIRED_COLUMNS
		}
		if _is_empty_row(values):
			continue
		if _is_banner_row(
			values["day"], values["time"], values["topic"], values["stakeholder"], values["description"]
		):
			continue

		day_number = _parse_day_number(values["day"])
		if day_number:
			current_day = day_number
			current_day_label = _cell_text(values["day"]) or f"Day {day_number}"
			session_index = 0

		if current_day is None:
			errors.append(f"Row {excel_row}: session appears before any Day header.")
			continue

		time_label = _cell_text(values["time"])
		topic = _cell_text(values["topic"])
		session_type = classify_session_type(time_label, topic)
		if not topic and session_type not in {"break", "lunch"}:
			# Carry time-only rows that are not breaks are invalid
			if not time_label:
				continue
			errors.append(f"Row {excel_row}: Topic is required unless the row is a break/lunch.")
			continue

		session_index += 1
		title = _session_title(time_label, topic, session_type, session_index)
		session_key = f"crt-d{current_day}-s{session_index:02d}"
		link_notes = []
		content_links = parse_content_links(values["content link"])
		raw_links = _cell_text(values["content link"])
		if raw_links and not content_links:
			link_notes.append(raw_links)

		description = _cell_text(values["description"])
		if link_notes:
			description = (description + "\n\n" if description else "") + "\n".join(link_notes)

		sessions.append(
			{
				"session_key": session_key,
				"day_number": current_day,
				"day_label": current_day_label or f"Day {current_day}",
				"session_index": session_index,
				"session_type": session_type,
				"time_label": time_label,
				"duration_minutes": parse_duration_minutes(time_label),
				"stakeholder": _cell_text(values["stakeholder"]),
				"topic": title,
				"description": description,
				"content_links": content_links,
				"excel_row": excel_row,
				"source_sheet": sheet_name,
			}
		)

	if errors:
		frappe.throw(_("CRT Excel validation failed:\n{0}").format("\n".join(errors)))
	if not sessions:
		frappe.throw(_("No CRT sessions found in sheet {0}.").format(sheet_name))

	sessions = to_curriculum(sessions)
	if not sessions:
		frappe.throw(_("No PPT or content-backed CRT lessons found in sheet {0}.").format(sheet_name))

	days = []
	by_day = {}
	for session in sessions:
		by_day.setdefault(session["day_number"], []).append(session)
	for day_number in sorted(by_day):
		day_sessions = by_day[day_number]
		days.append(
			{
				"day_number": day_number,
				"day_label": day_sessions[0]["day_label"],
				"session_count": len(day_sessions),
				"sessions": day_sessions,
			}
		)

	return {
		"sheet": sheet_name,
		"sheets": wb.sheetnames,
		"columns": [h for h in headers if h],
		"days": days,
		"sessions": sessions,
		"day_count": len(days),
		"session_count": len(sessions),
	}


def _resolve_excel_path(file_url: str | None = None, file_name: str | None = None, use_bundled: int = 0) -> tuple[str, str]:
	if cint(use_bundled):
		for candidate in (IMAGE_DATA_PATH, BUNDLED_EXCEL):
			if os.path.exists(candidate):
				return candidate, os.path.basename(candidate)
		frappe.throw(_("Bundled CRT Excel not found in the image. Upload the workbook instead."))

	if file_name and frappe.db.exists("File", file_name):
		file_doc = frappe.get_doc("File", file_name)
		path = file_doc.get_full_path()
		if not path or not os.path.exists(path):
			frappe.throw(_("Uploaded Excel is missing on disk."))
		return path, file_doc.file_name or file_name

	if file_url:
		name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not name:
			frappe.throw(_("Uploaded Excel file not found."))
		file_doc = frappe.get_doc("File", name)
		path = file_doc.get_full_path()
		if not path or not os.path.exists(path):
			frappe.throw(_("Uploaded Excel is missing on disk."))
		return path, file_doc.file_name or os.path.basename(file_url)

	frappe.throw(_("Provide a File, file URL, or use_bundled=1."))


def _ensure_course() -> str:
	if frappe.db.exists("LMS Course", COURSE_SLUG):
		# The course already exists: an import updates its sessions, not its settings. Title,
		# description and the published/featured flags belong to whoever edits the course.
		return COURSE_SLUG

	course = frappe.get_doc(
		{
			"doctype": "LMS Course",
			"title": COURSE_TITLE,
			"short_introduction": "Infinity Learn Sales CRT — Classroom Readiness Training for Academic Counsellors.",
			"description": (
				"<p>Five-day Classroom Readiness Training covering Infinity Learn products, "
				"call flow, demo conduction, LSQ, and live calling for Academic Counsellors.</p>"
			),
			"published": 1,
			"published_on": nowdate(),
			"upcoming": 0,
			"featured": 1,
			"disable_self_learning": 0,
			"enable_certification": 1,
		}
	)
	course.append("instructors", {"instructor": frappe.session.user})
	course.insert(ignore_permissions=True)
	if course.name != COURSE_SLUG:
		frappe.rename_doc("LMS Course", course.name, COURSE_SLUG, force=True)
	return COURSE_SLUG


def _ensure_chapter(course: str, day_number: int, day_label: str) -> str:
	title = f"CRT {day_number}"
	existing = frappe.db.get_value(
		"Chapter Reference", {"parent": course, "idx": day_number}, "chapter"
	)
	if not existing:
		existing = frappe.db.get_value("Course Chapter", {"course": course, "title": title}, "name")
	if not existing:
		existing = frappe.db.get_value(
			"Course Chapter", {"course": course, "title": f"Day {day_number}"}, "name"
		)
	if not existing and day_label:
		existing = frappe.db.get_value("Course Chapter", {"course": course, "title": day_label}, "name")
	if existing:
		# Keep an existing day's name (admins rename days); only link it to its position.
		_ensure_chapter_reference(course, existing, day_number)
		return existing

	from lms.lms.day_journey import CRT_DAY_TITLES

	chapter = frappe.get_doc(
		{
			"doctype": "Course Chapter",
			"course": course,
			"title": CRT_DAY_TITLES.get(day_number, title),
		}
	)
	chapter.insert(ignore_permissions=True)
	_ensure_chapter_reference(course, chapter.name, day_number)
	return chapter.name


def _ensure_chapter_reference(course: str, chapter: str, idx: int):
	existing = frappe.db.get_value("Chapter Reference", {"parent": course, "chapter": chapter}, "name")
	if existing:
		frappe.db.set_value("Chapter Reference", existing, "idx", idx)
		return
	ref = frappe.new_doc("Chapter Reference")
	ref.update(
		{
			"chapter": chapter,
			"idx": idx,
			"parent": course,
			"parenttype": "LMS Course",
			"parentfield": "chapters",
		}
	)
	ref.insert(ignore_permissions=True)


def _ensure_lesson(course: str, chapter: str, session: dict) -> str:
	title = session["topic"][:140]
	existing_session = frappe.db.get_value("Sales CRT Session", session["session_key"], ["lesson"], as_dict=True)
	lesson_name = existing_session.lesson if existing_session else None
	content = _lesson_content_json(session)

	if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
		lesson = frappe.get_doc("Course Lesson", lesson_name)
		lesson.title = title
		lesson.chapter = chapter
		lesson.content = content
		lesson.body = session.get("description") or title
		lesson.include_in_preview = 1 if session["session_index"] == 1 else 0
		lesson.save(ignore_permissions=True)
	else:
		lesson = frappe.get_doc(
			{
				"doctype": "Course Lesson",
				"title": title,
				"course": course,
				"chapter": chapter,
				"content": content,
				"body": session.get("description") or title,
				"include_in_preview": 1 if session["session_index"] == 1 else 0,
			}
		)
		lesson.insert(ignore_permissions=True)
		lesson_name = lesson.name

	existing_ref = frappe.db.get_value("Lesson Reference", {"parent": chapter, "lesson": lesson_name}, "name")
	if existing_ref:
		frappe.db.set_value("Lesson Reference", existing_ref, "idx", session["session_index"])
	else:
		ref = frappe.new_doc("Lesson Reference")
		ref.update(
			{
				"lesson": lesson_name,
				"idx": session["session_index"],
				"parent": chapter,
				"parenttype": "Course Chapter",
				"parentfield": "lessons",
			}
		)
		ref.insert(ignore_permissions=True)
	return lesson_name


def _rekey_moved_session(course: str, session: dict):
	"""Re-attach a session that changed position in the Excel.

	Session keys are positional (`crt-d2-s03`), so inserting one row in the sheet used to shift every
	later session: each lesson was re-titled with the next session's content, and the last one was
	deleted along with its progress. Before treating a key as new, look for the same day+topic under
	another key and move that record onto the new key instead.
	"""
	key = session["session_key"]
	if frappe.db.exists("Sales CRT Session", key):
		return
	topic = (session.get("topic") or "").strip()
	if not topic:
		return
	moved = frappe.get_all(
		"Sales CRT Session",
		filters={"course": course, "day_number": session["day_number"], "topic": topic},
		pluck="name",
		limit=2,
	)
	if len(moved) != 1 or moved[0] == key:
		return  # ambiguous (the same topic twice in a day): leave it to the normal path
	from frappe.model.rename_doc import rename_doc

	rename_doc("Sales CRT Session", moved[0], key, force=True, ignore_permissions=True, show_alert=False)
	frappe.db.set_value("Sales CRT Session", key, "session_key", key, update_modified=False)


def _upsert_session(course: str, chapter: str, lesson: str, session: dict) -> str:
	payload = {
		"doctype": "Sales CRT Session",
		"session_key": session["session_key"],
		"course": course,
		"chapter": chapter,
		"lesson": lesson,
		"day_number": session["day_number"],
		"day_label": session["day_label"],
		"session_index": session["session_index"],
		"session_type": session["session_type"],
		"time_label": session["time_label"],
		"duration_minutes": session.get("duration_minutes"),
		"stakeholder": session.get("stakeholder"),
		"topic": session["topic"],
		"excel_row": session.get("excel_row"),
		"source_sheet": session.get("source_sheet"),
		"description": _html_description(session.get("description") or ""),
		"content_links": [{"label": l["label"], "url": l["url"]} for l in session.get("content_links") or []],
	}
	if frappe.db.exists("Sales CRT Session", session["session_key"]):
		doc = frappe.get_doc("Sales CRT Session", session["session_key"])
		doc.update({k: v for k, v in payload.items() if k != "doctype"})
		doc.set("content_links", payload["content_links"])
		doc.save(ignore_permissions=True)
		return "updated"
	doc = frappe.get_doc(payload)
	doc.insert(ignore_permissions=True)
	return "created"


def _apply_import(parsed: dict) -> dict:
	course = _ensure_course()
	if not can_modify_course(course) and "System Manager" not in frappe.get_roles():
		frappe.throw(_("You do not have permission to modify this course."), frappe.PermissionError)

	created = updated = 0
	keep_keys = set()
	chapter_by_day = {}

	for day in parsed["days"]:
		chapter = _ensure_chapter(course, day["day_number"], day["day_label"])
		chapter_by_day[day["day_number"]] = chapter
		for session in day["sessions"]:
			_rekey_moved_session(course, session)
			lesson = _ensure_lesson(course, chapter, session)
			action = _upsert_session(course, chapter, lesson, session)
			keep_keys.add(session["session_key"])
			if action == "created":
				created += 1
			else:
				updated += 1

	removed = 0
	stale = frappe.get_all(
		"Sales CRT Session",
		filters={"course": course, "session_key": ["not in", list(keep_keys)]},
		fields=["name", "lesson", "chapter"],
	)
	kept = 0
	for row in stale:
		has_progress = row.lesson and frappe.db.exists("LMS Course Progress", {"lesson": row.lesson})
		if has_progress:
			# Learners have already worked through this lesson. Drop the schedule row, but keep the
			# lesson and its progress: deleting it would orphan everyone's completion.
			frappe.delete_doc("Sales CRT Session", row.name, ignore_permissions=True, force=True)
			kept += 1
			continue
		if row.lesson and frappe.db.exists("Course Lesson", row.lesson):
			frappe.db.delete("Lesson Reference", {"lesson": row.lesson})
			frappe.delete_doc("Course Lesson", row.lesson, ignore_permissions=True, force=True)
		frappe.delete_doc("Sales CRT Session", row.name, ignore_permissions=True, force=True)
		removed += 1

	# Drop empty leftover chapters for this course
	keep_chapters = set(chapter_by_day.values())
	for chapter in frappe.get_all("Course Chapter", {"course": course}, ["name"]):
		if chapter.name in keep_chapters:
			continue
		has_session = frappe.db.exists("Sales CRT Session", {"chapter": chapter.name})
		if has_session:
			continue
		if frappe.db.exists("Lesson Reference", {"parent": chapter.name}):
			continue  # a day an admin built by hand, or lessons kept for their progress
		frappe.db.delete("Chapter Reference", {"chapter": chapter.name})
		frappe.db.delete("Lesson Reference", {"parent": chapter.name})
		frappe.delete_doc("Course Chapter", chapter.name, ignore_permissions=True, force=True)

	from lms.lms.ojt_engine import seed_ojt_scenarios

	seed_ojt_scenarios()
	frappe.db.commit()
	return {
		"course": course,
		"days_count": parsed["day_count"],
		"sessions_created": created,
		"sessions_updated": updated,
		"sessions_removed": removed,
		"session_count": parsed["session_count"],
		"sheet": parsed["sheet"],
	}


def _write_import_log(status: str, dry_run: int, source_file: str, parsed: dict | None, result: dict | None, error: str | None):
	doc = frappe.get_doc(
		{
			"doctype": "Sales CRT Import Log",
			"status": status,
			"dry_run": cint(dry_run),
			"source_file": source_file,
			"source_sheet": (parsed or {}).get("sheet"),
			"days_count": (result or parsed or {}).get("days_count") or (parsed or {}).get("day_count"),
			"sessions_created": (result or {}).get("sessions_created"),
			"sessions_updated": (result or {}).get("sessions_updated"),
			"sessions_removed": (result or {}).get("sessions_removed"),
			"course": (result or {}).get("course"),
			"error_message": error,
			"summary": json.dumps(result or {"preview": _preview_payload(parsed)} if parsed else {}, default=str, indent=2),
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


def _preview_payload(parsed: dict) -> dict:
	return {
		"sheet": parsed["sheet"],
		"sheets": parsed["sheets"],
		"columns": parsed["columns"],
		"day_count": parsed["day_count"],
		"session_count": parsed["session_count"],
		"days": [
			{
				"day_number": d["day_number"],
				"day_label": d["day_label"],
				"session_count": d["session_count"],
				"sessions": [
					{
						"session_key": s["session_key"],
						"session_index": s["session_index"],
						"session_type": s["session_type"],
						"time_label": s["time_label"],
						"duration_minutes": s["duration_minutes"],
						"stakeholder": s["stakeholder"],
						"topic": s["topic"],
						"excel_row": s["excel_row"],
						"link_count": len(s.get("content_links") or []),
					}
					for s in d["sessions"]
				],
			}
			for d in parsed["days"]
		],
	}


@frappe.whitelist()
def preview_import(file_url: str | None = None, file_name: str | None = None, use_bundled: int = 0):
	"""Validate the CRT Excel and return a dry-run preview. Does not write courses."""
	_ensure_can_import()
	path, source = _resolve_excel_path(file_url, file_name, use_bundled)
	parsed = parse_crt_workbook(path)
	preview = _preview_payload(parsed)
	log_name = _write_import_log("Preview", 1, source, parsed, None, None)
	preview["import_log"] = log_name
	preview["source_file"] = source
	return preview


@frappe.whitelist(methods=["POST"])
def ensure_demo_learner(email: str | None = None, password: str | None = None):
	"""Create or reset a learner-only account for local/user-side testing."""
	if not cint(frappe.conf.get("allow_demo_learner")):
		frappe.throw(
			_("Demo learner setup is disabled on this site."),
			frappe.PermissionError,
		)
	# This sets a password and strips roles, so it must never be usable against a real account:
	# only a System Manager may call it, and only for the fixed demo address.
	frappe.only_for("System Manager")
	email = (email or DEMO_LEARNER_EMAIL).strip().lower()
	if email != DEMO_LEARNER_EMAIL:
		frappe.throw(
			_("The demo learner account is {0}.").format(DEMO_LEARNER_EMAIL),
			frappe.PermissionError,
		)
	password = password or os.environ.get("DEMO_LEARNER_PASSWORD")
	if not password:
		frappe.throw(
			_("Set DEMO_LEARNER_PASSWORD in the environment or pass password explicitly."),
			frappe.ValidationError,
		)
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		user.enabled = 1
		user.send_welcome_email = 0
		user.new_password = password
		user.save(ignore_permissions=True)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Sales",
				"last_name": "Learner",
				"full_name": "Sales Learner",
				"username": "learner",
				"send_welcome_email": 0,
				"enabled": 1,
				"new_password": password,
			}
		)
		user.insert(ignore_permissions=True)
	user.add_roles("LMS Student")
	for role in ("System Manager", "Administrator", "Moderator", "Course Creator"):
		if role in frappe.get_roles(email):
			user.remove_roles(role)
	if frappe.db.exists("LMS Course", COURSE_SLUG) and not frappe.db.exists(
		"LMS Enrollment", {"course": COURSE_SLUG, "member": email}
	):
		frappe.get_doc(
			{"doctype": "LMS Enrollment", "course": COURSE_SLUG, "member": email}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"email": email, "roles": frappe.get_roles(email)}


def import_bundled_schedule():
	return import_schedule(use_bundled=1)


def _bundled_excel_path() -> str | None:
	for candidate in (IMAGE_DATA_PATH, BUNDLED_EXCEL):
		if os.path.exists(candidate):
			return candidate
	return None


def _crt_needs_import() -> bool:
	if not frappe.db.exists("LMS Course", COURSE_SLUG):
		return True
	if not frappe.db.exists("DocType", "Sales CRT Session"):
		return True
	return frappe.db.count("Sales CRT Session", {"course": COURSE_SLUG}) == 0


def ensure_bundled_crt_bootstrap():
	"""Import image-baked CRT Excel on first boot (Docker entrypoint). Idempotent."""
	path = _bundled_excel_path()
	if not path:
		return {"skipped": True, "reason": "Bundled CRT Excel not found in image."}
	if not _crt_needs_import():
		count = frappe.db.count("Sales CRT Session", {"course": COURSE_SLUG})
		return {"skipped": True, "reason": "CRT course already present.", "session_count": count}
	previous_user = frappe.session.user
	frappe.set_user("Administrator")
	source = os.path.basename(path)
	try:
		parsed = parse_crt_workbook(path)
		result = _apply_import(parsed)
		log_name = _write_import_log("Success", 0, source, parsed, result, None)
		frappe.db.commit()
		return {
			"imported": True,
			"course": COURSE_SLUG,
			"session_count": result.get("session_count"),
			"import_log": log_name,
			"source_file": source,
		}
	except Exception as exc:
		frappe.db.rollback()
		_write_import_log("Failed", 0, source, None, None, str(exc))
		raise
	finally:
		frappe.set_user(previous_user)


@frappe.whitelist(methods=["POST"])
def import_schedule(file_url: str | None = None, file_name: str | None = None, use_bundled: int = 0):
	"""Idempotent CRT Excel → LMS Course / chapters / lessons / Sales CRT Session."""
	_ensure_can_import()
	path, source = _resolve_excel_path(file_url, file_name, use_bundled)
	try:
		parsed = parse_crt_workbook(path)
		result = _apply_import(parsed)
		log_name = _write_import_log("Success", 0, source, parsed, result, None)
		result["import_log"] = log_name
		result["source_file"] = source
		result["preview"] = _preview_payload(parsed)
		return result
	except Exception as exc:
		_write_import_log("Failed", 0, source, None, None, str(exc))
		raise


def _session_links(session_name: str) -> list[dict]:
	return frappe.get_all(
		"Sales CRT Content Link",
		filters={"parent": session_name, "parenttype": "Sales CRT Session"},
		fields=["label", "url", "idx"],
		order_by="idx asc",
	)


def _chapter_numbers(course: str) -> dict[str, int]:
	rows = frappe.get_all(
		"Chapter Reference",
		filters={"parent": course},
		fields=["chapter", "idx"],
		order_by="idx asc",
	)
	return {row.chapter: cint(row.idx) for row in rows}


def _lesson_numbers(chapter: str) -> dict[str, int]:
	rows = frappe.get_all(
		"Lesson Reference",
		filters={"parent": chapter},
		fields=["lesson", "idx"],
		order_by="idx asc",
	)
	return {row.lesson: cint(row.idx) for row in rows}


@frappe.whitelist(allow_guest=True)
def get_schedule():
	"""Frontend-facing CRT schedule from Frappe (never hardcoded in the SPA)."""
	if not frappe.db.exists("LMS Course", COURSE_SLUG):
		return {
			"course": None,
			"title": COURSE_TITLE,
			"empty": True,
			"days": [],
			"message": "No CRT course yet. Import the Excel schedule from Desk or the Import page.",
		}

	course = frappe.get_doc("LMS Course", COURSE_SLUG)
	chapter_idx = _chapter_numbers(COURSE_SLUG)
	sessions = frappe.get_all(
		"Sales CRT Session",
		filters={"course": COURSE_SLUG},
		fields=[
			"name",
			"session_key",
			"day_number",
			"day_label",
			"session_index",
			"session_type",
			"time_label",
			"duration_minutes",
			"stakeholder",
			"topic",
			"description",
			"chapter",
			"lesson",
			"excel_row",
		],
		order_by="day_number asc, session_index asc",
	)

	lesson_idx_cache = {}
	days_map = {}
	for row in sessions:
		day = days_map.setdefault(
			row.day_number,
			{
				"day_number": row.day_number,
				"day_label": row.day_label or f"Day {row.day_number}",
				"chapter": row.chapter,
				"chapter_number": chapter_idx.get(row.chapter),
				"sessions": [],
			},
		)
		if row.chapter and row.chapter not in lesson_idx_cache:
			lesson_idx_cache[row.chapter] = _lesson_numbers(row.chapter)
		links = _session_links(row.name)
		day["sessions"].append(
			{
				"name": row.name,
				"session_key": row.session_key,
				"session_index": row.session_index,
				"session_type": row.session_type,
				"time_label": row.time_label,
				"duration_minutes": row.duration_minutes,
				"stakeholder": row.stakeholder,
				"topic": row.topic,
				"description": row.description,
				"excel_row": row.excel_row,
				"chapter": row.chapter,
				"lesson": row.lesson,
				"chapter_number": chapter_idx.get(row.chapter),
				"lesson_number": lesson_idx_cache.get(row.chapter, {}).get(row.lesson),
				"content_links": [{"label": l.label, "url": l.url} for l in links],
			}
		)

	days = []
	for day_number in sorted(days_map):
		day = days_map[day_number]
		learning = [s for s in day["sessions"] if s["session_type"] not in {"break", "lunch"}]
		day["session_count"] = len(day["sessions"])
		day["learning_count"] = len(learning)
		day["total_minutes"] = sum(cint(s.get("duration_minutes")) for s in day["sessions"])
		days.append(day)

	return {
		"course": COURSE_SLUG,
		"title": course.title,
		"short_introduction": course.short_introduction,
		"description": course.description,
		"empty": not days,
		"day_count": len(days),
		"session_count": len(sessions),
		"days": days,
	}


@frappe.whitelist(allow_guest=True)
def get_session(session_key: str | None = None, name: str | None = None):
	if not session_key and not name:
		frappe.throw(_("session_key is required"))
	key = session_key or name
	if not frappe.db.exists("Sales CRT Session", key):
		frappe.throw(_("CRT session not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("Sales CRT Session", key)
	chapter_idx = _chapter_numbers(doc.course)
	lesson_idx = _lesson_numbers(doc.chapter) if doc.chapter else {}
	return {
		"name": doc.name,
		"session_key": doc.session_key,
		"course": doc.course,
		"day_number": doc.day_number,
		"day_label": doc.day_label,
		"session_index": doc.session_index,
		"session_type": doc.session_type,
		"time_label": doc.time_label,
		"duration_minutes": doc.duration_minutes,
		"stakeholder": doc.stakeholder,
		"topic": doc.topic,
		"description": doc.description,
		"chapter": doc.chapter,
		"lesson": doc.lesson,
		"chapter_number": chapter_idx.get(doc.chapter),
		"lesson_number": lesson_idx.get(doc.lesson),
		"content_links": [{"label": row.label, "url": row.url} for row in doc.content_links],
	}
