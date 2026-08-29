"""Secure, view-only PDF access for lesson content."""

import json
import os
from urllib.parse import unquote, urlparse

import frappe
from frappe import _

from lms.lms.utils import (
	can_modify_course,
	get_membership,
	has_course_instructor_role,
	has_moderator_role,
)

TOKEN_EXPIRY_SECONDS = 300
CACHE_PREFIX = "lms_secure_pdf:"


@frappe.whitelist()
def get_secure_pdf_token(file_url: str, lesson: str = None, course: str = None):
	"""Issue a short-lived token to stream a lesson PDF through the proxy."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to view this document."), frappe.PermissionError)

	file_url = _normalize_file_url(file_url)
	verify_pdf_access(file_url, lesson=lesson, course=course)

	token = frappe.generate_hash(length=32)
	frappe.cache().set_value(
		f"{CACHE_PREFIX}{token}",
		{
			"file_url": file_url,
			"user": frappe.session.user,
			"lesson": lesson,
			"course": course,
		},
		expires_in_sec=TOKEN_EXPIRY_SECONDS,
	)

	if lesson:
		log_pdf_view(lesson, file_url)

	return {"token": token, "expires_in": TOKEN_EXPIRY_SECONDS}


@frappe.whitelist(methods=["GET", "POST"])
def serve_secure_pdf(token: str):
	"""Stream PDF bytes for a valid token. Never expose the raw storage URL."""
	if not token:
		frappe.throw(_("Invalid or expired link."), frappe.PermissionError)

	cache_key = f"{CACHE_PREFIX}{token}"
	data = frappe.cache().get_value(cache_key)
	if not data:
		frappe.throw(_("Invalid or expired link."), frappe.PermissionError)

	if data.get("user") != frappe.session.user:
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	file_url = data.get("file_url")
	file_path = _resolve_file_path(file_url)
	if not file_path or not os.path.isfile(file_path):
		frappe.throw(_("File not found."))

	filename = file_doc_name(file_url)

	with open(file_path, "rb") as handle:
		frappe.response["filename"] = filename
		frappe.response["filecontent"] = handle.read()

	frappe.response["type"] = "download"
	frappe.response["content_type"] = "application/pdf"
	frappe.response["display_content_as"] = "inline"


def verify_pdf_access(file_url: str, lesson: str = None, course: str = None):
	file_url = _normalize_file_url(file_url)

	if not _file_exists(file_url):
		if lesson and course and _user_can_edit_course_content(course):
			if _file_referenced_in_lesson(lesson, file_url):
				frappe.throw(
					_(
						"This file is missing from the server. The lesson still references it - please upload the document again."
					),
					frappe.ValidationError,
				)
		frappe.throw(_("File not found."), frappe.PermissionError)

	if lesson:
		if not course:
			course = frappe.db.get_value("Course Lesson", lesson, "course")
		_verify_lesson_pdf_access(file_url, lesson, course)
		return

	if course and _user_can_edit_course_content(course):
		return

	if not _file_in_accessible_lesson(file_url):
		frappe.throw(_("You are not authorized to view this document."), frappe.PermissionError)


def _verify_lesson_pdf_access(file_url: str, lesson: str, course: str):
	lesson_course = frappe.db.get_value("Course Lesson", lesson, "course")
	if lesson_course != course:
		frappe.throw(_("You are not authorized to view this document."), frappe.PermissionError)

	if not _user_has_lesson_access(lesson, course):
		frappe.throw(_("You are not authorized to view this document."), frappe.PermissionError)

	# Instructors, moderators, and course creators may preview before save.
	if _user_can_edit_course_content(course):
		return

	if _file_referenced_in_course(course, file_url):
		return

	frappe.throw(_("This file is not part of the lesson."), frappe.PermissionError)


def _user_has_lesson_access(lesson: str, course: str) -> bool:
	fields = frappe.db.get_value(
		"Course Lesson",
		lesson,
		["include_in_preview"],
		as_dict=True,
	)
	if not fields:
		return False

	return bool(
		fields.include_in_preview
		or get_membership(course)
		or _user_can_edit_course_content(course)
	)


def _user_can_edit_course_content(course: str) -> bool:
	return bool(
		can_modify_course(course)
		or has_course_instructor_role()
		or has_moderator_role()
		or frappe.session.user == "Administrator"
	)


def _file_exists(file_url: str) -> bool:
	if frappe.db.exists("File", {"file_url": file_url}):
		return True

	basename = os.path.basename(unquote(urlparse(file_url).path))
	if basename and frappe.db.exists("File", {"file_name": basename}):
		return True

	return bool(_file_path_on_disk(file_url))


def _file_referenced_in_course(course: str, file_url: str) -> bool:
	lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course},
		fields=["name", "content", "body", "instructor_content", "instructor_notes"],
	)

	for row in lessons:
		if _file_referenced_in_lesson(row.name, file_url, lesson_doc=row):
			return True
	return False


def _file_referenced_in_lesson(lesson: str, file_url: str, lesson_doc: dict = None) -> bool:
	variants = _file_url_variants(file_url)
	if not lesson_doc:
		lesson_doc = frappe.db.get_value(
			"Course Lesson",
			lesson,
			["content", "body", "instructor_content", "instructor_notes"],
			as_dict=True,
		)
	if not lesson_doc:
		return False

	for field in ("content", "body", "instructor_content", "instructor_notes"):
		value = lesson_doc.get(field) or ""
		if _text_references_file(value, variants):
			return True
		if field in ("content", "instructor_content") and _editorjs_references_file(value, file_url):
			return True

	return _file_attached_to_lesson(lesson, file_url)


def _file_url_variants(file_url: str) -> set:
	normalized = _normalize_file_url(file_url)
	path = urlparse(normalized).path or normalized
	decoded_path = unquote(path)
	basename = os.path.basename(decoded_path)
	without_slash = path.lstrip("/")
	private_path = path.replace("/files/", "/private/files/", 1) if path.startswith("/files/") else ""

	variants = {normalized, path, decoded_path, without_slash, basename}
	if private_path:
		variants.add(private_path)
	return {v for v in variants if v}


def _text_references_file(text: str, variants: set) -> bool:
	for variant in variants:
		if variant and variant in text:
			return True
	return False


def _editorjs_references_file(content: str, file_url: str) -> bool:
	try:
		data = json.loads(content)
	except (TypeError, ValueError):
		return False

	target = _normalize_file_url(file_url)
	target_name = os.path.basename(unquote(urlparse(target).path))

	for block in data.get("blocks") or []:
		block_data = block.get("data") or {}
		block_url = block_data.get("file_url") or block_data.get("file") or ""
		if not block_url:
			continue
		if _urls_match(block_url, target):
			return True
		block_name = os.path.basename(unquote(urlparse(_normalize_file_url(block_url)).path))
		if target_name and block_name and target_name == block_name:
			return True
	return False


def _urls_match(url_a: str, url_b: str) -> bool:
	try:
		return _normalize_file_url(url_a) == _normalize_file_url(url_b)
	except frappe.PermissionError:
		return False


def _file_attached_to_lesson(lesson: str, file_url: str) -> bool:
	basename = os.path.basename(unquote(urlparse(_normalize_file_url(file_url)).path))
	filters = {"attached_to_doctype": "Course Lesson", "attached_to_name": lesson}
	if frappe.db.exists("File", {**filters, "file_url": file_url}):
		return True
	if basename and frappe.db.exists("File", {**filters, "file_name": basename}):
		return True
	return False


def _file_in_accessible_lesson(file_url: str) -> bool:
	variants = _file_url_variants(file_url)
	seen = set()

	for variant in variants:
		if not variant or variant in seen:
			continue
		seen.add(variant)

		for field in ("content", "body", "instructor_content", "instructor_notes"):
			lessons = frappe.get_all(
				"Course Lesson",
				filters={field: ["like", f"%{variant}%"]},
				fields=["name", "course", "include_in_preview"],
			)
			for row in lessons:
				membership = get_membership(row.course)
				if row.include_in_preview or membership or can_modify_course(row.course):
					return True
	return False


def log_pdf_view(lesson: str, file_url: str):
	if not frappe.db.exists("DocType", "LMS PDF View Log"):
		return

	frappe.get_doc(
		{
			"doctype": "LMS PDF View Log",
			"lesson": lesson,
			"member": frappe.session.user,
			"file_url": file_url,
		}
	).insert(ignore_permissions=True)


def _normalize_file_url(file_url: str) -> str:
	if not file_url:
		frappe.throw(_("File not found."), frappe.PermissionError)
	if file_url.startswith("http://") or file_url.startswith("https://"):
		from urllib.parse import urlparse

		parsed = urlparse(file_url)
		file_url = parsed.path
	if not file_url.startswith("/"):
		file_url = f"/{file_url}"
	return file_url


def _resolve_file_path(file_url: str) -> str:
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		basename = os.path.basename(unquote(urlparse(file_url).path))
		file_name = frappe.db.get_value("File", {"file_name": basename}, "name")
	if file_name:
		file_doc = frappe.get_doc("File", file_name)
		return file_doc.get_full_path()
	return _file_path_on_disk(file_url)


def _file_path_on_disk(file_url: str) -> str:
	normalized = _normalize_file_url(file_url)
	path = unquote(urlparse(normalized).path)

	if path.startswith("/private/files/"):
		relative = path[len("/private/files/") :]
		candidate = frappe.get_site_path("private", "files", relative)
	elif path.startswith("/files/"):
		relative = path[len("/files/") :]
		candidate = frappe.get_site_path("public", "files", relative)
	else:
		return ""

	return candidate if candidate and os.path.isfile(candidate) else ""


def file_doc_name(file_url: str) -> str:
	return frappe.db.get_value("File", {"file_url": file_url}, "file_name") or "document.pdf"


