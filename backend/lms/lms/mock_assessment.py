"""Constants and helpers for LMS Mock Assessment."""

import json

import frappe
from frappe import _

MOCK_SECTIONS = [
	{
		"key": "technical_efficacy",
		"label": "Technical efficacy",
		"description": "Tool usage, debugging ability, syntax accuracy, and handling technical queries.",
		"criteria": [
			{"key": "tool_usage", "label": "Tool usage"},
			{"key": "debugging", "label": "Debugging ability"},
			{"key": "syntax_accuracy", "label": "Syntax accuracy"},
			{"key": "technical_queries", "label": "Handling technical queries"},
		],
	},
	{
		"key": "curriculum_knowledge",
		"label": "Curriculum knowledge",
		"description": "Session objectives, curriculum alignment, theoretical accuracy, and topic connection.",
		"criteria": [
			{"key": "session_objectives", "label": "Session objectives"},
			{"key": "curriculum_alignment", "label": "Curriculum alignment"},
			{"key": "theoretical_accuracy", "label": "Theoretical accuracy"},
			{"key": "topic_connection", "label": "Topic connection"},
		],
	},
	{
		"key": "session_delivery",
		"label": "Session delivery with real-time examples",
		"description": "Use of examples, analogies, application-based questions, and engagement.",
		"criteria": [
			{"key": "examples", "label": "Use of examples"},
			{"key": "analogies", "label": "Analogies"},
			{"key": "application_questions", "label": "Application-based questions"},
			{"key": "engagement", "label": "Engagement"},
		],
	},
	{
		"key": "communication_skill",
		"label": "Communication skill",
		"description": "Language clarity, pace, two-way communication, and patience with learners.",
		"criteria": [
			{"key": "language_clarity", "label": "Language clarity"},
			{"key": "pace", "label": "Pace"},
			{"key": "two_way_communication", "label": "Two-way communication"},
			{"key": "patience", "label": "Patience with learners"},
		],
	},
	{
		"key": "time_management",
		"label": "Time management",
		"description": "Coverage within time, balance of theory/practical, avoiding diversions, and session structure.",
		"criteria": [
			{"key": "coverage_within_time", "label": "Coverage within time"},
			{"key": "theory_practical_balance", "label": "Balance of theory/practical"},
			{"key": "avoiding_diversions", "label": "Avoiding diversions"},
			{"key": "session_structure", "label": "Session structure"},
		],
	},
]

GRADE_OPTIONS = [f"Grade {i}" for i in range(1, 10)]
DURATION_OPTIONS = ["15", "30", "45", "60"]
ASSESSMENT_TYPE_OPTIONS = ["Mock", "VIVA", "Demo"]


def default_evaluation_sections():
	sections = []
	for section in MOCK_SECTIONS:
		sections.append(
			{
				"key": section["key"],
				"label": section["label"],
				"rating": 0,
				"comment": "",
				"criteria": [
					{"key": c["key"], "label": c["label"], "met": False} for c in section["criteria"]
				],
			}
		)
	return sections


def parse_evaluation_sections(raw):
	if not raw:
		return default_evaluation_sections()
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except json.JSONDecodeError:
			return default_evaluation_sections()
	if isinstance(raw, list):
		return raw
	return default_evaluation_sections()


def serialize_evaluation_sections(sections):
	return json.dumps(sections) if sections is not None else None


def format_mock_list_row(doc):
	submitted = doc.published_on or doc.modified
	return {
		"name": doc.name,
		"title": doc.title,
		"status": doc.status,
		"overall_rating": doc.overall_rating,
		"assessment_score_percent": doc.assessment_score_percent,
		"submitted_on": submitted,
		"submitted_on_display": frappe.utils.formatdate(submitted, "dd MMM yyyy")
		if submitted
		else "",
		"is_visible": doc.status == "Published",
	}


def format_mock_detail(doc, for_student=False):
	sections = parse_evaluation_sections(doc.evaluation_sections)
	return {
		"name": doc.name,
		"title": doc.title,
		"status": doc.status,
		"batch": doc.batch,
		"member": doc.member,
		"instructor_name": doc.instructor_name,
		"mock_date": doc.mock_date,
		"batch_brand": doc.batch_brand,
		"grade_observed": doc.grade_observed,
		"evaluator_name": doc.evaluator_name,
		"duration_minutes": doc.duration_minutes,
		"topic_observed": doc.topic_observed,
		"assessment_type": doc.assessment_type,
		"attendance_percent": doc.attendance_percent,
		"assessment_score_percent": doc.assessment_score_percent,
		"evaluation_sections": sections,
		"overall_rating": doc.overall_rating,
		"strengths": doc.strengths,
		"areas_of_improvement": doc.areas_of_improvement,
		"needs_mentorship": bool(frappe.utils.cint(doc.needs_mentorship)),
		"remock_needed": bool(frappe.utils.cint(doc.remock_needed)),
		"needs_retraining": bool(frappe.utils.cint(doc.needs_retraining)),
		"attachment": doc.attachment,
		"published_on": doc.published_on,
		"published_on_display": frappe.utils.formatdate(doc.published_on, "dd MMM yyyy")
		if doc.published_on
		else "",
		"for_student": for_student,
	}


def learner_mock_status_label(member: str, batch: str) -> str:
	"""Dashboard Mock column: latest published/draft state."""
	latest = frappe.get_all(
		"LMS Mock Assessment",
		filters={"member": member, "batch": batch},
		fields=["status"],
		order_by="modified desc",
		limit=1,
	)
	if not latest:
		return "—"

	status = latest[0].status
	if status == "Published":
		return _("Published")
	if status == "Draft":
		return _("Draft")
	return status or "—"
