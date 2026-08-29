"""Whitelisted APIs for LMS Mock Assessment."""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from lms.lms.mock_assessment import (
	ASSESSMENT_TYPE_OPTIONS,
	DURATION_OPTIONS,
	GRADE_OPTIONS,
	MOCK_SECTIONS,
	default_evaluation_sections,
	format_mock_detail,
	format_mock_list_row,
	learner_mock_status_label,
	parse_evaluation_sections,
	serialize_evaluation_sections,
)


def _ensure_analytics_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator"}):
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)


def _ensure_instructor_mock_access(batch: str | None = None, member: str | None = None):
	_ensure_analytics_access()
	if batch and not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))
	if member and batch:
		if not frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": member}):
			frappe.throw(_("Learner is not enrolled in this batch"))


def _get_mock_doc(name: str, batch: str | None = None, member: str | None = None):
	if not frappe.db.exists("LMS Mock Assessment", name):
		frappe.throw(_("Mock assessment not found"))
	doc = frappe.get_doc("LMS Mock Assessment", name)
	if batch and doc.batch != batch:
		frappe.throw(_("Mock assessment does not belong to this batch"))
	if member and doc.member != member:
		frappe.throw(_("Mock assessment does not belong to this learner"))
	return doc


def _apply_mock_payload(doc, data: dict):
	if isinstance(data, str):
		data = json.loads(data)

	for field in (
		"title",
		"instructor_name",
		"mock_date",
		"batch_brand",
		"grade_observed",
		"evaluator_name",
		"duration_minutes",
		"topic_observed",
		"assessment_type",
		"strengths",
		"areas_of_improvement",
		"attachment",
	):
		if field in data:
			doc.set(field, data.get(field))

	for field in ("attendance_percent", "assessment_score_percent"):
		if field in data and data.get(field) not in (None, ""):
			doc.set(field, flt(data.get(field)))

	if "overall_rating" in data:
		raw_rating = data.get("overall_rating")
		if raw_rating in (None, ""):
			doc.overall_rating = None
		else:
			doc.overall_rating = cint(raw_rating)

	for field in ("needs_mentorship", "remock_needed", "needs_retraining"):
		if field in data:
			doc.set(field, 1 if data.get(field) else 0)

	if "evaluation_sections" in data:
		sections = data.get("evaluation_sections")
		if isinstance(sections, str):
			sections = json.loads(sections)
		doc.evaluation_sections = serialize_evaluation_sections(parse_evaluation_sections(sections))


@frappe.whitelist()
def get_mock_assessment_form_options():
	"""Section templates and dropdown options for the mock wizard."""
	_ensure_analytics_access()
	return {
		"sections": MOCK_SECTIONS,
		"default_sections": default_evaluation_sections(),
		"grade_options": GRADE_OPTIONS,
		"duration_options": DURATION_OPTIONS,
		"assessment_type_options": ASSESSMENT_TYPE_OPTIONS,
	}


@frappe.whitelist()
def list_learner_mock_assessments(batch: str, member: str):
	"""List mock assessments for a learner (instructor analytics)."""
	_ensure_instructor_mock_access(batch, member)
	rows = frappe.get_all(
		"LMS Mock Assessment",
		filters={"batch": batch, "member": member},
		fields=[
			"name",
			"title",
			"status",
			"overall_rating",
			"assessment_score_percent",
			"modified",
			"published_on",
		],
		order_by="modified desc",
	)
	return [format_mock_list_row(frappe._dict(row)) for row in rows]


@frappe.whitelist()
def get_mock_assessment(name: str, batch: str | None = None, member: str | None = None):
	"""Full mock assessment for edit/view (instructor)."""
	_ensure_instructor_mock_access(batch, member)
	doc = _get_mock_doc(name, batch, member)
	return format_mock_detail(doc)


@frappe.whitelist()
def save_mock_assessment(
	batch: str,
	member: str,
	data: dict | str | None = None,
	name: str | None = None,
):
	"""Create or update a draft mock assessment."""
	_ensure_instructor_mock_access(batch, member)
	if isinstance(data, str):
		data = json.loads(data)

	data = data or {}
	title = (data.get("title") or "").strip()
	if not title:
		frappe.throw(_("Mock title is required."))

	if name:
		doc = _get_mock_doc(name, batch, member)
		if doc.status == "Published" and not data.get("allow_published_edit"):
			frappe.throw(_("Published mocks cannot be edited. Unpublish first or create a new mock."))
	else:
		doc = frappe.new_doc("LMS Mock Assessment")
		doc.batch = batch
		doc.member = member
		doc.status = "Draft"

	_apply_mock_payload(doc, data)
	doc.title = title
	if doc.status != "Published":
		doc.status = "Draft"
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "saved": True, "status": doc.status}


@frappe.whitelist()
def publish_mock_assessment(name: str, batch: str, member: str):
	"""Publish mock so the learner can see it."""
	_ensure_instructor_mock_access(batch, member)
	doc = _get_mock_doc(name, batch, member)
	if not doc.title:
		frappe.throw(_("Mock title is required before publishing."))
	doc.status = "Published"
	doc.published_on = now_datetime()
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "status": doc.status, "published": True}


@frappe.whitelist()
def toggle_mock_assessment_visibility(name: str, batch: str, member: str):
	"""Toggle between Published and Draft (visibility for learner)."""
	_ensure_instructor_mock_access(batch, member)
	doc = _get_mock_doc(name, batch, member)
	if doc.status == "Published":
		doc.status = "Draft"
		doc.published_on = None
	else:
		doc.status = "Published"
		doc.published_on = now_datetime()
	doc.save(ignore_permissions=True)
	return {
		"name": doc.name,
		"status": doc.status,
		"is_visible": doc.status == "Published",
	}


@frappe.whitelist()
def delete_mock_assessment(name: str, batch: str, member: str):
	"""Delete a draft mock assessment."""
	_ensure_instructor_mock_access(batch, member)
	doc = _get_mock_doc(name, batch, member)
	if doc.status == "Published":
		frappe.throw(_("Published mocks cannot be deleted. Unpublish first."))
	frappe.delete_doc("LMS Mock Assessment", name, ignore_permissions=True)
	return {"deleted": True}


@frappe.whitelist()
def get_student_mock_assessments():
	"""Published mocks for the logged-in student."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	rows = frappe.get_all(
		"LMS Mock Assessment",
		filters={"member": user, "status": "Published"},
		fields=["name", "title", "overall_rating", "assessment_score_percent", "published_on", "evaluator_name"],
		order_by="published_on desc",
	)
	result = []
	for row in rows:
		result.append(
			{
				"name": row.name,
				"title": row.title,
				"overall_rating": row.overall_rating,
				"assessment_score_percent": row.assessment_score_percent,
				"evaluator_name": row.evaluator_name,
				"published_on_display": frappe.utils.formatdate(row.published_on, "dd MMM yyyy")
				if row.published_on
				else "",
			}
		)
	return result


@frappe.whitelist()
def get_student_mock_assessment(name: str):
	"""Published mock detail for the logged-in student."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	doc = frappe.get_doc("LMS Mock Assessment", name)
	if doc.member != user or doc.status != "Published":
		frappe.throw(_("Mock result not found."), frappe.PermissionError)

	return format_mock_detail(doc, for_student=True)


def get_learner_mock_status(member: str, batch: str) -> str:
	return learner_mock_status_label(member, batch)
