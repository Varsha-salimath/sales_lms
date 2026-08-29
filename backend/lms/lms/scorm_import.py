"""One-shot SCORM ZIP → LMS Course import for Genius LMS."""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from xml.dom.minidom import parseString

import frappe
from frappe import _
from frappe.utils import escape_html, nowdate

from lms.lms.api import add_lesson, check_for_malicious_code, extract_package, get_manifest_file
from lms.lms.utils import can_modify_course, generate_slug, has_course_instructor_role, has_moderator_role

NS_STRIP = re.compile(r"\{[^}]+\}")


def _local(tag: str) -> str:
	return NS_STRIP.sub("", tag or "")


def _text(node) -> str:
	if not node:
		return ""
	parts = []
	for child in node.childNodes:
		if child.nodeType == child.TEXT_NODE:
			parts.append(child.data)
	return "".join(parts).strip()


def _first_child(parent, local_name: str):
	if not parent:
		return None
	for child in parent.childNodes:
		if child.nodeType == child.ELEMENT_NODE and _local(child.tagName) == local_name:
			return child
	return None


def _children(parent, local_name: str):
	if not parent:
		return []
	return [
		child
		for child in parent.childNodes
		if child.nodeType == child.ELEMENT_NODE and _local(child.tagName) == local_name
	]


def parse_scorm_manifest(manifest_path: str) -> dict:
	"""Parse imsmanifest.xml into course title + SCO items."""
	with open(manifest_path, encoding="utf-8", errors="ignore") as handle:
		dom = parseString(handle.read())

	resources = {}
	for res in dom.getElementsByTagName("resource"):
		identifier = res.getAttribute("identifier")
		scorm_type = res.getAttribute("adlcp:scormtype") or res.getAttribute("adlcp:scormType")
		href = res.getAttribute("href")
		if identifier:
			resources[identifier] = {"href": href, "scorm_type": (scorm_type or "").lower()}

	orgs_parent = None
	for node in dom.getElementsByTagName("organizations"):
		orgs_parent = node
		break

	default_org = orgs_parent.getAttribute("default") if orgs_parent else ""
	organizations = _children(orgs_parent, "organization") if orgs_parent else []
	organization = None
	for org in organizations:
		if org.getAttribute("identifier") == default_org or not default_org:
			organization = org
			break
	if not organization and organizations:
		organization = organizations[0]

	course_title = _text(_first_child(organization, "title")) or "Imported SCORM Course"
	items = []

	def walk_items(parent):
		for item in _children(parent, "item"):
			title = _text(_first_child(item, "title")) or f"Module {len(items) + 1}"
			identifierref = item.getAttribute("identifierref")
			resource = resources.get(identifierref) if identifierref else None
			is_sco = bool(resource and resource.get("href") and resource.get("scorm_type") == "sco")
			if resource and resource.get("href") and not resource.get("scorm_type"):
				is_sco = True
			if is_sco:
				items.append({"title": title, "identifierref": identifierref, "href": resource["href"]})
			walk_items(item)

	if organization:
		walk_items(organization)

	if not items:
		for res in resources.values():
			if res.get("href") and (res.get("scorm_type") == "sco" or not res.get("scorm_type")):
				items.append({"title": course_title, "identifierref": "", "href": res["href"]})
				break

	return {"title": course_title, "items": items}


def _read_manifest_from_zip(zip_path: str) -> dict:
	with zipfile.ZipFile(zip_path, "r") as zf:
		manifest_name = None
		for name in zf.namelist():
			if name.endswith("imsmanifest.xml"):
				manifest_name = name
				break
		if not manifest_name:
			frappe.throw(_("imsmanifest.xml not found in SCORM package."))

		with tempfile.TemporaryDirectory() as tmp:
			zf.extract(manifest_name, tmp)
			manifest_path = os.path.join(tmp, manifest_name)
			return parse_scorm_manifest(manifest_path)


def _ensure_can_import():
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if not (
		has_moderator_role()
		or has_course_instructor_role()
		or "System Manager" in frappe.get_roles()
	):
		frappe.throw(_("You do not have permission to import SCORM courses."), frappe.PermissionError)


def _safe_chapter_title(title: str, idx: int) -> str:
	clean = re.sub(r"[^\w\s\-]", "", title or f"Module {idx}").strip()
	return (clean or f"Module {idx}")[:140]


def _attach_chapter_reference(course: str, chapter: str, idx: int):
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
	ref.insert()


def cint_truthy(value) -> bool:
	return str(value).lower() in {"1", "true", "yes", "y"}


def import_scorm_course(
	file_name: str,
	course_title: str | None = None,
	course_name: str | None = None,
	publish: int = 1,
	scan_package: int = 1,
) -> dict:
	"""
	Create an LMS Course from an uploaded SCORM ZIP File doc name.

	Returns course name, title, and chapter list.
	"""
	_ensure_can_import()

	if not file_name or not frappe.db.exists("File", file_name):
		frappe.throw(_("SCORM package file not found."))

	file_doc = frappe.get_doc("File", file_name)
	zip_path = file_doc.get_full_path()
	if not zip_path or not os.path.exists(zip_path):
		frappe.throw(_("Uploaded SCORM package is missing on disk."))

	# Always scan SCORM packages in Genius (fail closed on malware patterns)
	check_for_malicious_code(zip_path)

	parsed = _read_manifest_from_zip(zip_path)
	title = (course_title or parsed["title"] or "Imported SCORM Course").strip()
	items = parsed["items"]
	if not items:
		frappe.throw(_("No SCO launch items found in SCORM manifest."))

	if course_name:
		slug = frappe.scrub(course_name)
		if frappe.db.exists("LMS Course", slug):
			frappe.throw(_("Course {0} already exists.").format(slug))
	else:
		slug = generate_slug(title, "LMS Course")

	course = frappe.get_doc(
		{
			"doctype": "LMS Course",
			"title": title,
			"short_introduction": _("Imported from SCORM package"),
			"description": f"<p>{escape_html(title)}</p>",
			"published": 1 if cint_truthy(publish) else 0,
			"published_on": nowdate() if cint_truthy(publish) else None,
			"upcoming": 0,
		}
	)
	course.append("instructors", {"instructor": frappe.session.user})
	course.insert()

	# Honor custom course_name/slug (LMS Course autoname is title-based)
	if course.name != slug:
		frappe.rename_doc("LMS Course", course.name, slug, force=True)
		course = frappe.get_doc("LMS Course", slug)

	if not can_modify_course(course.name):
		frappe.throw(_("You do not have permission to modify this course."), frappe.PermissionError)

	extract_path = extract_package(course.name, "package", frappe._dict(name=file_name))
	manifest_path = get_manifest_file(extract_path)
	if not manifest_path:
		frappe.throw(_("imsmanifest.xml not found after extract."))

	manifest_rel = manifest_path.split("public")[1]
	package_rel = extract_path.split("public")[1]
	chapters_created = []

	for idx, item in enumerate(items, start=1):
		chapter_title = _safe_chapter_title(item["title"], idx)
		launch_abs = os.path.realpath(os.path.join(os.path.dirname(manifest_path), item["href"]))
		extract_root = os.path.realpath(extract_path)
		if not (launch_abs == extract_root or launch_abs.startswith(extract_root + os.sep)):
			frappe.throw(_("Invalid launch path in SCORM package."))
		launch_rel = launch_abs.split("public")[1]

		chapter = frappe.new_doc("Course Chapter")
		chapter.update(
			{
				"title": chapter_title,
				"course": course.name,
				"is_scorm_package": 1,
				"scorm_package": file_name,
				"scorm_package_path": package_rel,
				"manifest_file": manifest_rel,
				"launch_file": launch_rel,
			}
		)
		chapter.insert()
		add_lesson(chapter_title, chapter.name, course.name, 1)
		_attach_chapter_reference(course.name, chapter.name, idx)
		chapters_created.append(
			{"name": chapter.name, "title": chapter_title, "launch_file": launch_rel}
		)

	course.reload()
	course.lessons = frappe.db.count("Course Lesson", {"course": course.name})
	course.save()

	return {
		"name": course.name,
		"title": course.title,
		"chapters": chapters_created,
		"published": course.published,
	}
