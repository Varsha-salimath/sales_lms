# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Sales CRT 1–5 → Training Evaluation → OJT → Certificate journey APIs."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_fullname, now_datetime

from lms.lms.ojt_engine import (
	AUDIT_CRITERIA,
	advance_after_learner,
	evaluate_attempt,
	opening_customer_line,
	seed_ojt_scenarios,
)
from lms.lms.sales_crt import COURSE_SLUG, COURSE_TITLE
from lms.lms.utils import get_course_outline

# Lesson-title keywords mapped to Excel / Audit Sample evaluation categories.
CRITERION_KEYWORDS = {
	"Product knowledge": (
		"product",
		"foundation",
		"test prep",
		"math champ",
		"target exam",
		"belief",
		"infinity",
	),
	"Process understanding": ("lsq", "process", "sop", "call flow", "disposition"),
	"Communication": ("calling", "live class", "etiquette", "roles"),
	"Sales approach": ("call flow", "demo", "pitch", "conduction"),
	"Customer handling": ("calling", "objection", "parent"),
	"Objection handling": ("objection", "difference between"),
	"Pitching ability": ("pitch", "demo", "session"),
	"Product positioning": ("foundation", "test prep", "math champ", "position"),
	"Process adherence": ("lsq", "calling", "audit"),
	"Confidence": ("live class", "calling", "demo"),
	"Sales readiness": ("calling", "certificate", "live class"),
	"Introduction": ("role", "belief", "introduction"),
	"Rapport Building": ("etiquette", "call flow"),
	"Need Generation": ("need", "lsq", "discovery"),
	"Session Pitching": ("pitch", "demo", "product"),
	"Closing": ("closing", "certificate", "calling"),
}


def _require_login():
	if frappe.session.user in (None, "Guest"):
		frappe.throw(_("Please log in to continue."), frappe.AuthenticationError)


def _is_staff(user: str | None = None) -> bool:
	"""Instructors, managers and admins: every day open, no viva gate (see access.bypasses_progression)."""
	user = user or frappe.session.user
	from lms.lms import access

	if access.learner_preview(user):
		return False
	roles = set(frappe.get_roles(user))
	if roles & {"System Manager", "Administrator", "Moderator", "Course Creator"}:
		return True
	return access.bypasses_progression(user)


def _own(member: str):
	if member != frappe.session.user and not _is_staff():
		frappe.throw(_("You can only access your own training records."), frappe.PermissionError)


def _ensure_enrolled(member: str) -> str:
	if not frappe.db.exists("LMS Course", COURSE_SLUG):
		return ""
	if not frappe.db.exists("LMS Enrollment", {"course": COURSE_SLUG, "member": member}):
		frappe.get_doc(
			{"doctype": "LMS Enrollment", "course": COURSE_SLUG, "member": member}
		).insert(ignore_permissions=True)
	return COURSE_SLUG


def _crt_states(member: str) -> list[dict]:
	staff = _is_staff(member)
	outline = get_course_outline(COURSE_SLUG, progress=True) or []
	crts = []
	# Day 1 opens only after the Hello ILians joining form is in.
	from lms.lms.hello_ilians import is_required as hello_ilians_required

	prev_complete = staff or not hello_ilians_required(member)
	# Each day ends with a voice viva; until it is passed the day is "viva_pending" and the next stays locked.
	from lms.lms import sales_viva

	viva_on = sales_viva.is_required() and not staff
	viva_passed = sales_viva.passed_days(member) if (viva_on or staff) else set()
	for idx in range(1, 6):
		chapter = next((c for c in outline if cint(c.get("idx")) == idx), None)
		lessons = (chapter or {}).get("lessons") or []
		total = len(lessons)
		done = sum(1 for les in lessons if les.get("is_complete") or les.get("progress") == "Complete")
		if not chapter or total == 0:
			state = "locked" if not staff and not prev_complete else "empty"
			progress = 0
		elif not prev_complete and not staff:
			state = "locked"
			progress = 0
		elif done >= total and viva_on and idx not in viva_passed:
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
		current_lesson = None
		for les in lessons:
			if not (les.get("is_complete") or les.get("progress") == "Complete"):
				current_lesson = les
				break
		if not current_lesson and lessons:
			current_lesson = lessons[-1]
		crts.append(
			{
				"crt_number": idx,
				"title": (chapter or {}).get("title") or f"CRT {idx}",
				"chapter": (chapter or {}).get("name"),
				"state": state,
				"progress": progress,
				"lessons_total": total,
				"lessons_done": done,
				"viva": sales_viva.day_viva_state(member, idx) if viva_on and state == "viva_pending" else {
					"required": viva_on,
					"passed": idx in viva_passed,
					# Staff aren't gated but can try any day's viva once it's switched on.
					"can_try": bool(staff and sales_viva.is_configured()),
				},
				"current_lesson": {
					"name": current_lesson.get("name"),
					"title": current_lesson.get("title"),
					"number": current_lesson.get("number"),
				}
				if current_lesson
				else None,
				"lessons": [
					{
						"name": les.get("name"),
						"title": les.get("title"),
						"number": les.get("number"),
						"complete": bool(les.get("is_complete") or les.get("progress") == "Complete"),
						"locked": False if staff else bool(les.get("locked")),
					}
					for les in lessons
				],
			}
		)
		prev_complete = state == "completed"
	return crts


def _all_crts_complete(crts: list[dict]) -> bool:
	return all(row["state"] == "completed" and row["lessons_total"] > 0 for row in crts)


def _evaluation_doc(member: str):
	name = frappe.db.get_value(
		"Sales Training Evaluation", {"member": member, "course": COURSE_SLUG}, "name"
	)
	return frappe.get_doc("Sales Training Evaluation", name) if name else None


def _compute_evaluation(member: str, crts: list[dict]) -> dict:
	outline = get_course_outline(COURSE_SLUG, progress=True) or []
	lessons = []
	for chapter in outline:
		for les in chapter.get("lessons") or []:
			lessons.append(les)

	scores = []
	for criterion, keywords in CRITERION_KEYWORDS.items():
		matched = []
		for les in lessons:
			title = (les.get("title") or "").lower()
			if any(k in title for k in keywords):
				matched.append(les)
		if not matched:
			continue
		done = sum(1 for les in matched if les.get("is_complete") or les.get("progress") == "Complete")
		score = round((done / len(matched)) * 100, 1)
		scores.append(
			{
				"criterion": criterion,
				"score": score,
				"max_score": 100,
				"source": f"{done}/{len(matched)} related CRT sessions completed",
				"notes": "From your CRT lesson completion on matching topics.",
			}
		)

	# Always include Audit Sample pillars even if keyword miss — use CRT progress mix.
	crt_avg = round(sum(c["progress"] for c in crts) / max(1, len(crts)), 1)
	have = {s["criterion"] for s in scores}
	for pillar in AUDIT_CRITERIA:
		if pillar in have:
			continue
		scores.append(
			{
				"criterion": pillar,
				"score": crt_avg,
				"max_score": 100,
				"source": "Overall CRT 1–5 completion",
				"notes": "No dedicated session title mapped; scored from CRT completion.",
			}
		)

	overall = round(sum(s["score"] for s in scores) / max(1, len(scores)), 1)
	ranked = sorted(scores, key=lambda s: s["score"], reverse=True)
	strengths = [s["criterion"] for s in ranked if s["score"] >= 70][:4]
	improvements = [s["criterion"] for s in ranked if s["score"] < 70][-4:]
	if overall >= 80:
		readiness = "Ready for OJT"
	elif overall >= 60:
		readiness = "Nearly ready — practise weak areas in OJT"
	else:
		readiness = "Needs more CRT practice before live calling"
	return {
		"scores": scores,
		"overall_score": overall,
		"readiness": readiness,
		"strengths": ", ".join(strengths) or "Complete more CRT sessions to surface strengths.",
		"improvements": ", ".join(improvements) or "Maintain this standard into OJT.",
		"next_step": "Unlock OJT and complete at least one live sales simulation.",
	}


def _ojt_eligibility(crts: list[dict], evaluation, member: str | None = None) -> dict:
	member = member or frappe.session.user
	if _is_staff(member):
		return {
			"eligible": True,
			"locked": False,
			"reason": "Staff preview — OJT is unlocked for admin access.",
		}
	missing = []
	if not _all_crts_complete(crts):
		incomplete = [f"CRT {c['crt_number']}" for c in crts if c["state"] != "completed"]
		missing.append("Complete " + ", ".join(incomplete) + " first.")
	if not evaluation or evaluation.status != "Completed":
		missing.append("Complete the Sales training evaluation after CRT 5.")
	return {
		"eligible": not missing,
		"locked": bool(missing),
		"reason": " ".join(missing)
		if missing
		else "CRT 1–5 and training evaluation are complete. OJT is unlocked.",
	}


def _certificate_eligibility(member: str, crts: list[dict], evaluation) -> dict:
	finished_ojt = frappe.db.count(
		"Sales OJT Attempt",
		{"member": member, "course": COURSE_SLUG, "status": "Completed"},
	)
	missing = []
	if not _all_crts_complete(crts):
		missing.append("Finish CRT 1–5.")
	if not evaluation or evaluation.status != "Completed":
		missing.append("Complete training evaluation.")
	if not finished_ojt:
		missing.append("Complete at least one OJT simulation.")
	existing = frappe.db.get_value(
		"LMS Certificate", {"member": member, "course": COURSE_SLUG}, "name"
	)
	return {
		"eligible": not missing,
		"locked": bool(missing),
		"reason": " ".join(missing) if missing else "You can claim your Sales CRT certificate.",
		"certificate": existing,
		"ojt_completed": finished_ojt,
		"feedback_required": False,
	}


def _session_milestones(crts: list[dict]) -> list[dict]:
	items = []
	current = next((c for c in crts if c["state"] in {"available", "in_progress", "viva_pending"}), None)
	if current and current.get("current_lesson"):
		items.append(
			{
				"kind": "current",
				"title": current["current_lesson"]["title"],
				"detail": f"{current['title']} · continue this session",
				"crt_number": current["crt_number"],
			}
		)
	for crt in crts:
		if crt["state"] == "available":
			items.append(
				{
					"kind": "milestone",
					"title": f"{crt['title']} unlocked",
					"detail": "Start this CRT when you are ready.",
					"crt_number": crt["crt_number"],
				}
			)
			break
	if _all_crts_complete(crts):
		items.append(
			{
				"kind": "evaluation",
				"title": "Training evaluation",
				"detail": "CRT classroom training is complete. Review your Sales rating.",
			}
		)
		items.append(
			{
				"kind": "ojt",
				"title": "OJT unlock",
				"detail": "Live sales simulation is the next stage after evaluation.",
			}
		)
	else:
		left = next((c for c in crts if c["state"] != "completed"), None)
		if left:
			items.append(
				{
					"kind": "upcoming",
					"title": f"Complete {left['title']}",
					"detail": "Sessions done. Take the voice viva to finish the day."
					if left["state"] == "viva_pending"
					else f"{left['lessons_done']}/{left['lessons_total']} sessions done.",
					"crt_number": left["crt_number"],
				}
			)
	return items[:4]


@frappe.whitelist()
def get_onboarding_home():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	if not frappe.db.exists("LMS Course", COURSE_SLUG):
		return {
			"empty": True,
			"message": "Sales CRT has not been imported yet.",
			"learner": {"name": member, "full_name": get_fullname(member)},
		}
	crts = _crt_states(member)
	evaluation = _evaluation_doc(member)
	staff = _is_staff(member)
	ojt = _ojt_eligibility(crts, evaluation, member)
	cert = _certificate_eligibility(member, crts, evaluation)
	current = next((c for c in crts if c["state"] in {"available", "in_progress"}), None)
	if not current:
		current = next((c for c in reversed(crts) if c["state"] == "completed"), crts[0])
	overall = round(sum(c["progress"] for c in crts) / 5, 1)
	eval_status = evaluation.status if evaluation else None
	if not eval_status:
		if staff or _all_crts_complete(crts):
			eval_status = "Ready"
		else:
			eval_status = "Locked"
	return {
		"empty": False,
		"course": COURSE_SLUG,
		"title": COURSE_TITLE,
		"learner": {"name": member, "full_name": get_fullname(member)},
		"is_staff": staff,
		"overall_progress": overall,
		"crts": crts,
		"current": current,
		"milestones": _session_milestones(crts),
		"evaluation": {
			"status": eval_status,
			"overall_score": evaluation.overall_score if evaluation else None,
			"readiness": evaluation.readiness if evaluation else None,
		},
		"ojt": ojt,
		"certificate": cert,
		"hello_ilians": _hello_ilians_state(member, staff),
	}


def _hello_ilians_state(member, staff):
	from lms.lms.hello_ilians import is_submitted

	submitted = is_submitted(member)
	return {"required": not staff, "submitted": submitted}


@frappe.whitelist()
def get_crt_detail(crt_number: int):
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crt_number = cint(crt_number)
	crts = _crt_states(member)
	crt = next((c for c in crts if c["crt_number"] == crt_number), None)
	if not crt:
		frappe.throw(_("CRT {0} was not found.").format(crt_number))
	sessions = []
	if frappe.db.exists("DocType", "Sales CRT Session"):
		sessions = frappe.get_all(
			"Sales CRT Session",
			filters={"course": COURSE_SLUG, "day_number": crt_number},
			fields=[
				"session_key",
				"topic",
				"time_label",
				"stakeholder",
				"description",
				"session_type",
				"lesson",
				"day_label",
			],
			order_by="session_index asc",
		)
	return {"crt": crt, "journey": crts, "sessions": sessions, "course": COURSE_SLUG}


@frappe.whitelist()
def get_evaluation():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crts = _crt_states(member)
	staff = _is_staff(member)
	locked = not staff and not _all_crts_complete(crts)
	doc = _evaluation_doc(member)
	payload = {
		"locked": locked,
		"reason": "" if staff else ("Complete CRT 1–5 to unlock your Sales training evaluation." if locked else ""),
		"crts_complete": staff or not locked,
		"evaluation": None,
	}
	if doc:
		payload["evaluation"] = {
			"name": doc.name,
			"status": doc.status,
			"overall_score": doc.overall_score,
			"readiness": doc.readiness,
			"strengths": doc.strengths,
			"improvements": doc.improvements,
			"next_step": doc.next_step,
			"scores": [
				{"criterion": r.criterion, "score": r.score, "max_score": r.max_score, "source": r.source, "notes": r.notes}
				for r in doc.scores
			],
		}
	return payload


@frappe.whitelist()
def complete_evaluation():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crts = _crt_states(member)
	if not _is_staff(member) and not _all_crts_complete(crts):
		frappe.throw(_("Complete CRT 1–5 before generating your training evaluation."))
	computed = _compute_evaluation(member, crts)
	doc = _evaluation_doc(member)
	if not doc:
		doc = frappe.new_doc("Sales Training Evaluation")
		doc.member = member
		doc.course = COURSE_SLUG
	doc.status = "Completed"
	doc.overall_score = computed["overall_score"]
	doc.readiness = computed["readiness"]
	doc.strengths = computed["strengths"]
	doc.improvements = computed["improvements"]
	doc.next_step = computed["next_step"]
	doc.set("scores", [])
	for row in computed["scores"]:
		doc.append("scores", row)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return get_evaluation()


@frappe.whitelist()
def get_ojt_state():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	seed_ojt_scenarios()
	crts = _crt_states(member)
	evaluation = _evaluation_doc(member)
	elig = _ojt_eligibility(crts, evaluation, member)
	scenarios = frappe.get_all(
		"Sales OJT Scenario",
		filters={"enabled": 1},
		fields=["name", "title", "source_crt", "customer_name", "customer_role", "objective", "sort_order"],
		order_by="sort_order asc",
	)
	attempts = frappe.get_all(
		"Sales OJT Attempt",
		filters={"member": member, "course": COURSE_SLUG},
		fields=["name", "scenario", "status", "overall_score", "started_at", "completed_at"],
		order_by="modified desc",
	)
	return {
		**elig,
		"scenarios": scenarios,
		"attempts": attempts,
		"certificate": _certificate_eligibility(member, crts, evaluation),
	}


@frappe.whitelist()
def start_ojt(scenario: str):
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crts = _crt_states(member)
	evaluation = _evaluation_doc(member)
	elig = _ojt_eligibility(crts, evaluation, member)
	if not elig["eligible"]:
		frappe.throw(_(elig["reason"]))
	if not frappe.db.exists("Sales OJT Scenario", scenario):
		frappe.throw(_("Unknown OJT scenario."))
	open_attempt = frappe.db.get_value(
		"Sales OJT Attempt",
		{"member": member, "scenario": scenario, "status": "In Progress"},
		"name",
	)
	if open_attempt:
		return get_ojt_attempt(open_attempt)
	doc_scenario = frappe.get_doc("Sales OJT Scenario", scenario)
	now = now_datetime()
	attempt = frappe.get_doc(
		{
			"doctype": "Sales OJT Attempt",
			"member": member,
			"course": COURSE_SLUG,
			"scenario": scenario,
			"status": "In Progress",
			"started_at": now,
			"beat_index": 0,
		}
	)
	attempt.append(
		"messages",
		{
			"role": "customer",
			"content": opening_customer_line(doc_scenario),
			"beat_key": "open",
			"created_at": now,
		},
	)
	attempt.insert(ignore_permissions=True)
	return get_ojt_attempt(attempt.name)


@frappe.whitelist()
def get_ojt_attempt(attempt: str):
	_require_login()
	doc = frappe.get_doc("Sales OJT Attempt", attempt)
	_own(doc.member)
	scenario = frappe.get_doc("Sales OJT Scenario", doc.scenario)
	return {
		"attempt": {
			"name": doc.name,
			"status": doc.status,
			"overall_score": doc.overall_score,
			"strengths": doc.strengths,
			"improvements": doc.improvements,
			"beat_index": doc.beat_index,
			"started_at": doc.started_at,
			"completed_at": doc.completed_at,
			"messages": [
				{"role": m.role, "content": m.content, "beat_key": m.beat_key, "created_at": m.created_at}
				for m in doc.messages
			],
			"scores": [
				{"criterion": s.criterion, "score": s.score, "max_score": s.max_score, "notes": s.notes}
				for s in doc.scores
			],
		},
		"scenario": {
			"name": scenario.name,
			"title": scenario.title,
			"customer_name": scenario.customer_name,
			"customer_role": scenario.customer_role,
			"objective": scenario.objective,
			"context": scenario.context,
			"instructions": scenario.instructions,
			"source_crt": scenario.source_crt,
		},
	}


@frappe.whitelist()
def send_ojt_turn(attempt: str, message: str):
	_require_login()
	doc = frappe.get_doc("Sales OJT Attempt", attempt)
	_own(doc.member)
	if doc.status == "Completed":
		frappe.throw(_("This simulation is already complete."))
	text = (message or "").strip()
	if not text:
		frappe.throw(_("Say something to the parent before sending."))
	result = advance_after_learner(doc, text)
	if result["finished"]:
		_persist_ojt_score(doc)
	else:
		doc.save(ignore_permissions=True)
	return {**get_ojt_attempt(doc.name), "hint": result.get("hint")}


@frappe.whitelist()
def finish_ojt(attempt: str):
	_require_login()
	doc = frappe.get_doc("Sales OJT Attempt", attempt)
	_own(doc.member)
	if doc.status != "Completed":
		_persist_ojt_score(doc)
	return get_ojt_attempt(doc.name)


def _persist_ojt_score(doc):
	result = evaluate_attempt(doc)
	doc.status = "Completed"
	doc.completed_at = now_datetime()
	doc.overall_score = result["overall_score"]
	doc.strengths = result["strengths"]
	doc.improvements = result["improvements"]
	doc.set("scores", [])
	for row in result["scores"]:
		doc.append("scores", row)
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_certificate_state():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crts = _crt_states(member)
	evaluation = _evaluation_doc(member)
	return _certificate_eligibility(member, crts, evaluation)


@frappe.whitelist()
def claim_certificate():
	_require_login()
	member = frappe.session.user
	_ensure_enrolled(member)
	crts = _crt_states(member)
	evaluation = _evaluation_doc(member)
	state = _certificate_eligibility(member, crts, evaluation)
	if not state["eligible"]:
		frappe.throw(_(state["reason"]))
	if state["certificate"]:
		return state
	from lms.lms.doctype.lms_certificate.lms_certificate import create_certificate

	cert = create_certificate(COURSE_SLUG)
	state["certificate"] = cert.get("name") if isinstance(cert, dict) else getattr(cert, "name", cert)
	state["eligible"] = True
	state["locked"] = False
	return state


def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None
	return f"`tabSales Training Evaluation`.member = {frappe.db.escape(user)}"


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	return getattr(doc, "member", None) == user


def get_ojt_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None
	return f"`tabSales OJT Attempt`.member = {frappe.db.escape(user)}"


def has_ojt_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True
	return getattr(doc, "member", None) == user
