# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Voice viva — the last step of every day in a day-by-day course (Sales CRT first).

Asha (Gemini Live native audio) asks ~5 questions generated fresh from that day's content.
The browser streams the mic straight to Gemini with a short-lived token minted here, so the
API key never leaves the server, and the question paper stays on the server too: Asha only
receives each question through the get_next_stem tool call when it is time to ask it.

How an answer is delivered matters as much as what is said. The browser measures, per question,
the time to start answering, pauses, speaking time and whether the learner left the tab; the
server keeps its own clock as a floor. After the call a text model scores each answer against the
day's facts, and timing becomes a Fluency score plus flags for the trainer (never an automatic fail).

Three attempts per day; a Training Manager can grant three more. Passing unlocks the next day.
Gemini Live engine (token minting, turn-taking, stem tools) by Saraga — see docs/AI_VIVA_PRD.md.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, now_datetime

COURSE_SLUG = "sales-crt"

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_AUTH_TOKENS_URL = "https://generativelanguage.googleapis.com/v1alpha/auth_tokens"
GEMINI_LIVE_WS = (
	"wss://generativelanguage.googleapis.com/ws/"
	"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained"
)
KEY_ENV_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY")

STEMS_PER_VIVA = 5
MAX_SESSION_PROBES = 2
MIN_ANSWER_WORDS = 5
# Below this many questions the day has no usable content: refuse to start rather than score a 0.
MIN_STEMS_TO_START = 3
ATTEMPTS_PER_DAY = 3
PASS_MARK = 60
READY_MARK = 80
TIME_LIMIT_S = 240  # a 3–4 minute conversation; the browser ends the call here
STALE_AFTER_S = 15 * 60  # an attempt left "In Progress" this long was abandoned
HTTP_TIMEOUT_S = 45
MAX_TEXT_CHARS = 2500
PACK_CHARS = 14000
PAUSE_MS = 2000  # silences longer than this inside an answer count as pauses

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _setting(name: str, default: str = "") -> str:
	return str(frappe.conf.get(name.lower()) or os.environ.get(name) or default).strip()


def live_model() -> str:
	return _setting("GEMINI_LIVE_MODEL", "gemini-3.8-live")


def text_model() -> str:
	return _setting("GEMINI_TEXT_MODEL", "gemini-flash-latest")


def voice_name() -> str:
	return _setting("GEMINI_VOICE", "Kore")


def _gemini_key() -> str:
	for name in KEY_ENV_NAMES:
		raw = (os.environ.get(name) or frappe.conf.get(name.lower()) or "").strip().strip('"').strip("'")
		if raw:
			return raw
	return ""


def is_configured() -> bool:
	return bool(_gemini_key())


def is_required(course: str = COURSE_SLUG) -> bool:
	"""The viva gates a course's days when the course asks for it and it can actually be taken."""
	if not is_configured() or cint(frappe.conf.get("crt_viva_required", 1)) != 1:
		return False
	return bool(frappe.db.get_value("LMS Course", course, "day_viva"))


def _assert_key() -> str:
	key = _gemini_key()
	if not key:
		frappe.throw(_("The voice viva is not switched on yet. Please tell your trainer."), frappe.ValidationError)
	return key


# ---------------------------------------------------------------------------
# Gemini HTTP
# ---------------------------------------------------------------------------


def _gemini_error_message(body: bytes, status: int) -> str:
	try:
		parsed = json.loads(body.decode("utf-8", errors="replace"))
	except ValueError:
		return _("Gemini request failed ({0}).").format(status)
	err = parsed.get("error") if isinstance(parsed, dict) else None
	if isinstance(err, dict) and (err.get("message") or err.get("status")):
		return str(err.get("message") or err.get("status"))
	return _("Gemini request failed ({0}).").format(status)


def _gemini_json(url: str, payload: dict[str, Any], timeout: int = HTTP_TIMEOUT_S) -> dict[str, Any]:
	key = _assert_key()
	req = Request(
		url,
		data=json.dumps(payload).encode("utf-8"),
		method="POST",
		headers={"x-goog-api-key": key, "Content-Type": "application/json"},
	)
	try:
		with urlopen(req, timeout=timeout) as resp:
			raw = resp.read()
	except HTTPError as exc:
		body = exc.read() if exc.fp else b""
		frappe.throw(_gemini_error_message(body, exc.code), frappe.ValidationError)
	except URLError:
		frappe.throw(_("Could not reach Gemini. Check outbound HTTPS from the backend."), frappe.ValidationError)
	try:
		parsed = json.loads(raw.decode("utf-8"))
	except ValueError:
		frappe.throw(_("Gemini returned a non-JSON response."), frappe.ValidationError)
	return parsed if isinstance(parsed, dict) else {}


def _generate_json(system: str, prompt: str, schema: dict[str, Any], temperature: float = 0.4) -> Any:
	"""One text-model call that must return JSON matching `schema`."""
	payload = {
		"systemInstruction": {"parts": [{"text": system}]},
		"contents": [{"role": "user", "parts": [{"text": prompt}]}],
		"generationConfig": {
			"temperature": temperature,
			"responseMimeType": "application/json",
			"responseSchema": schema,
		},
	}
	parsed = _gemini_json(f"{GEMINI_API}/models/{text_model()}:generateContent", payload)
	parts = ((parsed.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
	text = "".join(p.get("text") or "" for p in parts).strip()
	if not text:
		frappe.throw(_("Gemini returned an empty answer."), frappe.ValidationError)
	return json.loads(text)


def _mint_live_token(setup: dict[str, Any]) -> str:
	now = datetime.now(timezone.utc)
	payload = {
		"uses": 4,
		"expireTime": (now + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
		"newSessionExpireTime": (now + timedelta(minutes=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
		"bidiGenerateContentSetup": setup,
	}
	name = (_gemini_json(GEMINI_AUTH_TOKENS_URL, payload, timeout=20).get("name") or "").strip()
	if not name:
		frappe.throw(_("Gemini did not issue a Live token."), frappe.ValidationError)
	return name


# ---------------------------------------------------------------------------
# Day content → question paper
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
	import html

	return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _editorjs_text(content: str) -> str:
	try:
		blocks = json.loads(content or "{}").get("blocks") or []
	except (ValueError, AttributeError):
		return _strip_html(content)
	out = []
	for b in blocks:
		data = b.get("data") or {}
		if b.get("type") in ("paragraph", "header"):
			out.append(_strip_html(data.get("text")))
		elif b.get("type") == "list":
			for item in data.get("items") or []:
				out.append("- " + _strip_html(item.get("content") if isinstance(item, dict) else item))
		elif b.get("type") == "markdown":
			out.append(_strip_html(data.get("text")))
	return "\n".join(x for x in out if x)


def _day_chapter(course: str, day: int) -> str | None:
	return frappe.db.get_value("Chapter Reference", {"parent": course, "idx": day}, "chapter")


def day_title(course: str, day: int) -> str:
	from lms.lms.day_journey import clean_title

	chapter = _day_chapter(course, day)
	title = frappe.db.get_value("Course Chapter", chapter, "title") if chapter else ""
	return clean_title(day, title) or _("Day {0}").format(day)


def course_title(course: str) -> str:
	return frappe.db.get_value("LMS Course", course, "title") or course


def _day_lessons(course: str, day: int) -> list[str]:
	chapter = _day_chapter(course, day)
	return frappe.get_all("Lesson Reference", {"parent": chapter}, pluck="lesson", order_by="idx") if chapter else []


def _day_quizzes(course: str, day: int) -> list[str]:
	"""Quizzes embedded in the day's lessons (works for any course)."""
	quizzes = []
	for lesson in _day_lessons(course, day):
		try:
			blocks = json.loads(frappe.db.get_value("Course Lesson", lesson, "content") or "{}").get("blocks") or []
		except ValueError:
			continue
		for b in blocks:
			quiz = (b.get("data") or {}).get("quiz") if b.get("type") == "quiz" else None
			if quiz and quiz not in quizzes and frappe.db.exists("LMS Quiz", quiz):
				quizzes.append(quiz)
	return quizzes


def _quiz_facts(course: str, day: int, limit: int = 40) -> list[str]:
	facts = []
	for quiz in _day_quizzes(course, day):
		for row in frappe.get_all("LMS Quiz Question", {"parent": quiz}, ["question"], order_by="idx"):
			q = frappe.db.get_value(
				"LMS Question",
				row.question,
				["question", "option_1", "option_2", "option_3", "option_4", "is_correct_1", "is_correct_2", "is_correct_3", "is_correct_4"],
				as_dict=True,
			)
			if not q:
				continue
			right = [q.get(f"option_{i}") for i in range(1, 5) if q.get(f"is_correct_{i}") and q.get(f"option_{i}")]
			if right:
				facts.append(f"Q: {_strip_html(q.question)} A: {'; '.join(_strip_html(r) for r in right)}")
	return facts[:limit]


def _day_count(course: str) -> int:
	return frappe.db.count("Chapter Reference", {"parent": course})


def _day_pack(course: str, day: int) -> str:
	"""Plain-text knowledge pack for one day (lessons, quiz facts, CRT session outlines), cached for an hour."""
	key = f"viva_pack:{course}:{day}"
	cached = frappe.cache().get_value(key)
	if cached:
		return cached
	parts = [f"{course_title(course)} — Day {day}: {day_title(course, day)}"]
	if course == COURSE_SLUG and frappe.db.exists("DocType", "Sales CRT Session"):
		sessions = frappe.get_all(
			"Sales CRT Session",
			{"course": course, "day_number": day, "session_type": ["in", ["session", "activity", "assessment", "calling"]]},
			["topic", "description"],
			order_by="session_index",
		)
		if sessions:
			parts.append("SESSIONS:\n" + "\n".join(f"- {s.topic}: {_strip_html(s.description)}" for s in sessions))
	for lesson in _day_lessons(course, day):
		row = frappe.db.get_value("Course Lesson", lesson, ["title", "content", "body"], as_dict=True) or {}
		text = _editorjs_text(row.get("content")) or _strip_html(row.get("body"))
		if text:
			parts.append(f"LESSON {row.get('title')}:\n{text}")
	facts = _quiz_facts(course, day)
	if len(facts) < 5 and day > 1:
		# A thin day (e.g. live-calling practice) is examined on what came before it.
		for earlier in range(1, day):
			facts += _quiz_facts(course, earlier, limit=8)
	if facts:
		parts.append("FACTS (from the quizzes, correct answers):\n" + "\n".join(facts))
	pack = "\n\n".join(parts)[:PACK_CHARS]
	frappe.cache().set_value(key, pack, expires_in_sec=3600)
	return pack


PAPER_SCHEMA = {
	"type": "OBJECT",
	"properties": {
		"questions": {
			"type": "ARRAY",
			"items": {
				"type": "OBJECT",
				"properties": {
					"concept": {"type": "STRING"},
					"stem": {"type": "STRING"},
					"probe": {"type": "STRING"},
					"model_answer": {"type": "STRING"},
					"key_points": {"type": "ARRAY", "items": {"type": "STRING"}},
				},
				"required": ["concept", "stem", "probe", "model_answer", "key_points"],
			},
		}
	},
	"required": ["questions"],
}


def _previous_stems(member: str, course: str, day: int) -> list[str]:
	stems = []
	for raw in frappe.get_all("Sales Viva Attempt", {"member": member, "course": course, "crt_number": day}, pluck="paper_json"):
		try:
			stems += [q.get("stem") for q in json.loads(raw or "[]") if q.get("stem")]
		except ValueError:
			pass
	return stems[-15:]


def _generate_paper(member: str, course: str, day: int) -> list[dict[str, Any]]:
	pack = _day_pack(course, day)
	avoid = _previous_stems(member, course, day)
	system = (
		"You write oral viva questions for new Infinity Learn sales associates (academic counsellors) "
		"at the end of a classroom training day. Questions are SPOKEN aloud by an examiner, so each stem is one "
		"natural sentence of at most 28 words. Mix recall of facts with practical 'a parent says…, what do you say?' "
		"situations. Every question must be answerable ONLY from the provided day content; never invent product "
		"facts, prices or numbers. Each question covers a different concept. The probe is a short follow-up asked "
		"only if the first answer is thin. model_answer is what a well-trained associate would say (2-4 sentences). "
		"key_points are 3-5 short checkable facts from the content."
	)
	prompt = (
		f"Write exactly {STEMS_PER_VIVA} questions for this day.\n"
		+ ("Do NOT reuse or closely paraphrase these earlier questions:\n- " + "\n- ".join(avoid) + "\n\n" if avoid else "")
		+ f"Variation seed: {secrets.token_hex(3)}\n\nDAY CONTENT:\n{pack}"
	)
	try:
		data = _generate_json(system, prompt, PAPER_SCHEMA, temperature=0.9)
		paper = [q for q in (data.get("questions") or []) if (q.get("stem") or "").strip()][:STEMS_PER_VIVA]
	except Exception:
		frappe.log_error(title="CRT viva: question generation failed", message=frappe.get_traceback())
		paper = []
	if len(paper) < STEMS_PER_VIVA:
		paper += _fallback_paper(course, day, STEMS_PER_VIVA - len(paper), [q["stem"] for q in paper] + avoid)
	for i, q in enumerate(paper, start=1):
		q["id"] = f"q{i}"
		q["key_points"] = [str(p) for p in (q.get("key_points") or [])][:6]
	return paper


def _fallback_paper(course: str, day: int, count: int, avoid: list[str]) -> list[dict[str, Any]]:
	"""If the text model is unavailable, turn the day's quiz facts into spoken questions."""
	import random

	facts = _quiz_facts(course, day, limit=60)
	for earlier in range(1, day):
		if len(facts) >= 10:
			break
		facts += _quiz_facts(course, earlier, limit=20)
	random.shuffle(facts)
	out = []
	for fact in facts:
		q, _sep, a = fact.partition(" A: ")
		q = q.removeprefix("Q: ").strip()
		# Multiple-choice wording ("Which of the following…", "NOT") doesn't work when spoken.
		if re.search(r"following|\bNOT\b|true or false|all of the above", q, flags=re.I):
			continue
		stem = q.rstrip("?").strip() + "?"
		if stem in avoid:
			continue
		out.append({"concept": q.removeprefix("Q: ")[:40], "stem": stem, "probe": "Can you explain why?", "model_answer": a, "key_points": [a]})
		if len(out) >= count:
			break
	return out


# ---------------------------------------------------------------------------
# Live session (Asha)
# ---------------------------------------------------------------------------

LIVE_TOOLS = [
	{
		"functionDeclarations": [
			{
				"name": "commit_answer",
				"behavior": "BLOCKING",
				"description": (
					"Call only when the learner finished a complete answer to the CURRENT question "
					"(a full thought, several sentences, or 'I don't know'). Never on a mid-sentence pause."
				),
				"parameters": {
					"type": "OBJECT",
					"properties": {
						"transcript": {"type": "STRING", "description": "What you heard, as complete as possible."},
						"complete": {"type": "BOOLEAN", "description": "True only if they finished the thought."},
					},
					"required": ["complete"],
				},
			},
			{
				"name": "get_next_stem",
				"behavior": "BLOCKING",
				"description": (
					"Return the next question to ask. Call at the very start, or after commit_answer returned "
					"allow_next_stem true. Never invent a question."
				),
				"parameters": {"type": "OBJECT", "properties": {"reason": {"type": "STRING"}}},
			},
			{
				"name": "finish_viva",
				"behavior": "BLOCKING",
				"description": "Call when all questions are done or time is up. Then say one closing sentence. Do not grade out loud.",
				"parameters": {"type": "OBJECT", "properties": {"reason": {"type": "STRING"}}},
			},
		]
	}
]


def _asha_system(course: str, day: int) -> str:
	return (
		"You are Asha, a friendly but firm Infinity Learn training examiner taking a short spoken viva "
		f"at the end of Day {day} ({day_title(course, day)}) of {course_title(course)}. This is an exam, not tutoring.\n"
		"Speak short, natural Indian English. Hinglish answers are fine.\n"
		"Pace: this is a brisk, natural conversation — like a real call with a parent, not a written exam. "
		"Someone who knows the material answers fluently; you do not give extra thinking time.\n"
		"Turn-taking:\n"
		"- A brief pause mid-sentence is normal. Never say 'take your time'.\n"
		"- Stay on the current question until commit_answer returns allow_next_stem true.\n"
		"- If a tool says awaiting_answer or incomplete, prompt once in two or three words ('Go on?', 'And?') and wait briefly.\n"
		"- If told the learner did not answer in time, say 'Okay, let's move on' and call commit_answer with complete true and transcript 'No answer'.\n"
		"- Call commit_answer only after a complete thought or 'I don't know'.\n"
		"- Call get_next_stem at the start and only after allow_next_stem is true.\n"
		"Rules:\n"
		"- Ask ONLY the question text returned by get_next_stem, in your own natural words. Never invent questions.\n"
		"- Never answer for the learner, hint, teach or complete their sentence.\n"
		"- One short neutral acknowledgement after an answer ('Okay', 'Thank you'), then the next question.\n"
		"- If commit_answer returns use_probe, ask that follow-up once and wait for a full answer.\n"
		"- If the learner asks you to repeat, repeat the current question once.\n"
		"- When the tools say no questions are left, call finish_viva and close in one sentence. Never read scores.\n"
		"- No small talk. If the learner goes off topic, bring them back to the current question."
	)


def _live_setup(course: str, day: int) -> dict[str, Any]:
	return {
		"model": f"models/{live_model()}",
		"generationConfig": {
			"responseModalities": ["AUDIO"],
			"temperature": 0.3,
			"speechConfig": {
				"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice_name()}},
				"languageCode": "en-IN",
			},
		},
		"systemInstruction": {"parts": [{"text": _asha_system(course, day)}]},
		"tools": LIVE_TOOLS,
		"realtimeInputConfig": {
			"automaticActivityDetection": {"disabled": True},
			"activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
			"turnCoverage": "TURN_INCLUDES_ONLY_ACTIVITY",
		},
		# Transcription language follows speechConfig.languageCode; the API rejects a per-field code.
		"inputAudioTranscription": {},
		"outputAudioTranscription": {},
	}


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


def _is_staff(user: str | None = None) -> bool:
	roles = set(frappe.get_roles(user or frappe.session.user))
	return bool(roles & {"System Manager", "Administrator", "Moderator", "Course Creator"})


def _journey_staff(user: str) -> bool:
	"""Staff skip the 'finish the sessions first' rule — unless they are in learner view."""
	from lms.lms.sales_journey import _is_staff as journey_staff

	return journey_staff(user)


def _require_login() -> str:
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	return frappe.session.user


def _attempts(member: str, course: str, day: int | None = None) -> list[dict]:
	rows = frappe.get_all(
		"Sales Viva Attempt",
		{"member": member, "course": course},
		["name", "crt_number", "chapter", "course", "attempt_no", "status", "overall_score", "knowledge_score", "fluency_score", "verdict", "started_at", "ended_at", "watch_outs"],
		order_by="creation asc",
	)
	# Match on where the day sits today, not on the number stored when the attempt was taken.
	return [r for r in rows if _resolve_day(r) == cint(day)] if day else rows


def _counts_as_attempt(row) -> bool:
	return row.status in ("Passed", "Not Passed", "Scoring")


def attempts_allowed(member: str, course: str, day: int) -> int:
	rows = frappe.get_all(
		"Sales Viva Unlock",
		{"member": member, "course": course},
		["extra_attempts", "crt_number", "chapter", "course"],
	)
	extra = sum(cint(r.extra_attempts) for r in rows if _resolve_day(r) == cint(day))
	return ATTEMPTS_PER_DAY + extra


def _expire_stale(member: str):
	"""Close attempts left open (tab closed, network lost): score what was answered, else abandon."""
	cutoff = now_datetime() - timedelta(seconds=STALE_AFTER_S)
	# "Scoring" is written before the grading call. If that call never returned (a restart, a save
	# error), the attempt would sit in Scoring for ever while still counting as one of three tries.
	for name in frappe.get_all(
		"Sales Viva Attempt", {"member": member, "status": "Scoring", "modified": ["<", cutoff]}, pluck="name"
	):
		doc = frappe.get_doc("Sales Viva Attempt", name)
		try:
			_finalize(doc, _state(doc), reason="recovered")
		except Exception:
			frappe.log_error(f"Viva rescore failed for {name}", "sales_viva")
	for name in frappe.get_all(
		"Sales Viva Attempt", {"member": member, "status": "In Progress", "started_at": ["<", cutoff]}, pluck="name"
	):
		doc = frappe.get_doc("Sales Viva Attempt", name)
		state = _state(doc)
		if state.get("turns"):
			_finalize(doc, state, reason="left")
		else:
			doc.status = "Abandoned"
			doc.ended_at = now_datetime()
			doc.save(ignore_permissions=True)


def day_viva_state(member: str, course: str, day: int) -> dict[str, Any]:
	"""Viva summary for one day, used by the journey and the viva page."""
	rows = _attempts(member, course, day)
	used = sum(1 for r in rows if _counts_as_attempt(r))
	allowed = attempts_allowed(member, course, day)
	passed = next((r for r in rows if r.status == "Passed"), None)
	scored = [r for r in rows if r.status in ("Passed", "Not Passed")]
	best = max(scored, key=lambda r: flt(r.overall_score), default=None)
	in_progress = next((r for r in reversed(rows) if r.status == "In Progress"), None)
	return {
		"required": is_required(course),
		"configured": is_configured(),
		"passed": bool(passed),
		"passed_attempt": passed.name if passed else None,
		"attempts_used": used,
		"attempts_allowed": allowed,
		"attempts_left": max(0, allowed - used),
		"blocked": not passed and used >= allowed,
		"best_score": flt(best.overall_score) if best else None,
		"last_attempt": scored[-1].name if scored else None,
		"in_progress": in_progress.name if in_progress else None,
		"history": [
			{
				"name": r.name,
				"attempt_no": r.attempt_no,
				"status": r.status,
				"overall_score": r.overall_score,
				"verdict": r.verdict,
				"date": r.started_at,
			}
			for r in rows
			if r.status != "In Progress"
		],
	}


def day_chapter(course: str, day: int) -> str | None:
	"""The chapter behind a day number right now."""
	return frappe.db.get_value("Chapter Reference", {"parent": course, "idx": cint(day)}, "chapter")


def _resolve_day(row) -> int:
	"""A record's day today: from its chapter if it has one, else the number it was written with.

	Day numbers are chapter positions, so deleting or reordering a day used to move everyone's
	passes and unlocks onto a different day.
	"""
	chapter = row.get("chapter") if isinstance(row, dict) else getattr(row, "chapter", None)
	number = cint(row.get("crt_number") if isinstance(row, dict) else getattr(row, "crt_number", 0))
	if chapter:
		course = row.get("course") if isinstance(row, dict) else getattr(row, "course", None)
		idx = frappe.db.get_value("Chapter Reference", {"parent": course, "chapter": chapter}, "idx")
		if idx:
			return cint(idx)
	return number


def passed_days(member: str, course: str = COURSE_SLUG) -> set[int]:
	rows = frappe.get_all(
		"Sales Viva Attempt",
		{"member": member, "course": course, "status": "Passed"},
		["crt_number", "chapter", "course"],
	)
	return {_resolve_day(r) for r in rows}


def _state(doc) -> dict[str, Any]:
	try:
		return json.loads(doc.live_state_json or "{}")
	except ValueError:
		return {}


def _save_state(doc, state: dict[str, Any]):
	doc.live_state_json = json.dumps(state)
	doc.db_set("live_state_json", doc.live_state_json, update_modified=False)


def _paper(doc) -> list[dict[str, Any]]:
	try:
		return json.loads(doc.paper_json or "[]")
	except ValueError:
		return []


def _own_attempt(attempt: str):
	user = _require_login()
	doc = frappe.get_doc("Sales Viva Attempt", attempt)
	if doc.member != user:
		frappe.throw(_("This is not your viva."), frappe.PermissionError)
	return doc


def _course_day(course=None, day=None, crt_number=None) -> tuple[str, int]:
	"""Accept (course, day) or the older crt_number-only call (Sales CRT)."""
	from lms.lms.day_journey import parse_day

	course = course or COURSE_SLUG
	number = parse_day(day if day is not None else crt_number)
	if not frappe.db.exists("LMS Course", course) or number < 1 or number > _day_count(course):
		frappe.throw(_("Unknown day."))
	return course, number


@frappe.whitelist()
def get_viva_state(crt_number=None, course: str | None = None, day=None):
	"""What the viva page needs before starting: day, attempts, history, whether lessons are done."""
	member = _require_login()
	course, day = _course_day(course, day, crt_number)
	from lms.lms.content_scope import can_access
	from lms.lms.day_journey import day_slug, day_states, progression_applies

	if not can_access("LMS Course", course, member):
		frappe.throw(_("You don't have access to this course."), frappe.PermissionError)
	_expire_stale(member)
	row = next((d for d in day_states(member, course) if d["day"] == day), {})
	state = day_viva_state(member, course, day)
	lessons_done = bool(row) and row.get("lessons_total", 0) > 0 and row.get("lessons_done", 0) >= row.get("lessons_total", 0)
	reason = None
	if not state["configured"] or not frappe.db.get_value("LMS Course", course, "day_viva"):
		reason = "not_configured"
	elif state["passed"]:
		reason = "passed"
	elif state["blocked"]:
		reason = "blocked"
	elif progression_applies(course, member) and row.get("state") == "locked":
		# Days open in order. Someone who finished the sessions before the viva existed could
		# otherwise open a later day's viva directly by URL.
		reason = "day_locked"
	elif not lessons_done and progression_applies(course, member):
		reason = "lessons_pending"
	title = day_title(course, day)
	return {
		"course": course,
		"course_title": course_title(course),
		"day": day,
		"crt_number": day,
		"slug": day_slug(day, title),
		"title": title,
		"days_total": _day_count(course),
		"lessons_done": lessons_done,
		"lessons_total": row.get("lessons_total", 0),
		"lessons_completed": row.get("lessons_done", 0),
		"can_start": reason is None,
		"reason": reason,
		"questions": STEMS_PER_VIVA,
		"time_limit_s": TIME_LIMIT_S,
		"pass_mark": PASS_MARK,
		**state,
	}


@frappe.whitelist(methods=["POST"])
def start_attempt(crt_number=None, course: str | None = None, day=None):
	"""Generate a fresh paper, open an attempt and mint a Gemini Live token for it."""
	member = _require_login()
	course, day = _course_day(course, day, crt_number)
	info = get_viva_state(course=course, day=day)
	if not info["can_start"]:
		messages = {
			"not_configured": _("The voice viva is not switched on for this course."),
			"passed": _("You have already passed this day's viva."),
			"blocked": _("You have used all your attempts. Your Training Manager can unlock more."),
			"lessons_pending": _("Finish all of this day's sessions first."),
			"day_locked": _("Finish the earlier days first."),
		}
		frappe.throw(messages.get(info["reason"], _("You can't start the viva right now.")))
	# Only one live attempt at a time. An open attempt that already has answers is scored (and counts),
	# so restarting can't be used to preview questions for free; an empty one is just abandoned.
	for name in frappe.get_all("Sales Viva Attempt", {"member": member, "status": "In Progress"}, pluck="name"):
		old = frappe.get_doc("Sales Viva Attempt", name)
		old_state = _state(old)
		if old_state.get("turns"):
			_finalize(old, old_state, reason="left")
		else:
			old.db_set({"status": "Abandoned", "ended_at": now_datetime()})
	info = get_viva_state(course=course, day=day)
	if not info["can_start"]:
		frappe.throw(_("You have used all your attempts. Your Training Manager can unlock more."))

	setup = _live_setup(course, day)
	token = _mint_live_token(setup)  # before generating the paper: fail fast if Live is misconfigured
	paper = _generate_paper(member, course, day)
	if len(paper) < MIN_STEMS_TO_START:
		# No usable questions for this day: fail before opening an attempt, so a content gap can't
		# score the learner 0 and eat one of their three tries.
		frappe.throw(
			_("This day's viva has no questions yet. Tell your Training Manager — your attempts are untouched.")
		)
	doc = frappe.get_doc(
		{
			"doctype": "Sales Viva Attempt",
			"member": member,
			"course": course,
			"crt_number": day,
			"chapter": day_chapter(course, day),
			"attempt_no": info["attempts_used"] + 1,
			"status": "In Progress",
			"started_at": now_datetime(),
			"model": live_model(),
			"paper_json": json.dumps(paper),
			"live_state_json": json.dumps(
				{"asked": [], "current": None, "answered": True, "probe_active": False, "probe_used": False, "probes": 0, "turns": []}
			),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {
		"attempt": doc.name,
		"attempt_no": doc.attempt_no,
		"attempts_allowed": info["attempts_allowed"],
		"ws_url": GEMINI_LIVE_WS + "?access_token=" + quote(token, safe=""),
		"setup": setup,  # holds no questions: those arrive one at a time via get_next_stem
		"time_limit_s": TIME_LIMIT_S,
		"questions": len(paper),
		"title": info["title"],
	}


def _word_count(text: str) -> int:
	return len([w for w in (text or "").split() if w])


def _is_idk(text: str) -> bool:
	"""Did the learner pass on the question?

	Only a short utterance counts. "I'm not sure, but the fee is about twelve thousand" is an
	answer with a hedge in it, and treating it as a pass scored the whole turn zero.
	"""
	t = (text or "").lower().replace("’", "'").strip()
	if not t:
		return True
	if not re.search(r"\b(i don't know|i dont know|no idea|not sure|skip this|pata nahi|no answer)\b", t):
		return False
	return _word_count(t) <= 8


def _clean_metrics(raw: Any) -> dict[str, Any]:
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except ValueError:
			raw = {}
	raw = raw if isinstance(raw, dict) else {}
	out = {}
	for key in ("think_ms", "answer_ms", "speech_ms", "pause_count", "longest_pause_ms", "tab_switches", "fillers"):
		out[key] = max(0, min(cint(raw.get(key)), 30 * 60 * 1000))
	out["transcript"] = str(raw.get("transcript") or "")[:MAX_TEXT_CHARS]
	return out


def _payload_for_current(state, paper, error="", instruction="") -> dict[str, Any]:
	q = paper[state["current"]] if state.get("current") is not None else {}
	return {
		"error": error,
		"instruction": instruction,
		"allow_next_stem": False,
		"question": q.get("probe") if state.get("probe_active") else q.get("stem"),
		"question_number": len(state.get("asked") or []),
		"remaining_after_this": max(0, len(paper) - len(state.get("asked") or [])),
	}


def _record(state, paper, transcript: str, metrics: dict[str, Any]):
	"""Store (or extend, for a follow-up) the answer for the current question with its timing."""
	idx = state["current"]
	q = paper[idx]
	turn = next((t for t in state["turns"] if t["idx"] == idx), None)
	server_ms = int((time.time() - state.get("asked_at", time.time())) * 1000)
	text = metrics.get("transcript") if _word_count(metrics.get("transcript")) > _word_count(transcript) else transcript
	if not turn:
		turn = {
			"idx": idx,
			"question": q["stem"],
			"concept": q.get("concept"),
			"answer": "",
			"probe_asked": False,
			# Browser clock starts when Asha finishes speaking; the server's is only an upper bound.
			"think_ms": min(metrics["think_ms"], server_ms),
			"answer_ms": 0,
			"speech_ms": 0,
			"pause_count": 0,
			"longest_pause_ms": 0,
			"tab_switches": 0,
			"fillers": 0,
			"server_ms": 0,
		}
		state["turns"].append(turn)
	else:
		turn["probe_asked"] = True
	turn["answer"] = (turn["answer"] + ("\n[Follow-up] " if turn["answer"] else "") + (text or "")).strip()[:MAX_TEXT_CHARS * 2]
	for key in ("answer_ms", "speech_ms", "pause_count", "tab_switches", "fillers"):
		turn[key] += metrics[key]
	turn["longest_pause_ms"] = max(turn["longest_pause_ms"], metrics["longest_pause_ms"])
	turn["server_ms"] += server_ms


def _commit_answer(state, paper, args, metrics) -> dict[str, Any]:
	if state.get("current") is None:
		return {"error": "no_current_stem", "allow_next_stem": False, "instruction": "Call get_next_stem first."}
	if state.get("answered") and not state.get("probe_active"):
		# Asha committed this answer already (a repeated or cancelled tool call). Recording it twice
		# would append a phantom follow-up to the turn.
		return {
			"ok": True,
			"error": "already_recorded",
			"allow_next_stem": True,
			"instruction": "This answer is already recorded. Call get_next_stem.",
		}
	complete = args.get("complete")
	if isinstance(complete, str):
		complete = complete.strip().lower() in ("1", "true", "yes")
	transcript = str(args.get("transcript") or "").strip()
	heard = transcript if _word_count(transcript) >= _word_count(metrics.get("transcript")) else metrics.get("transcript")
	nudges = cint(state.get("nudges", 0))
	if not complete or not heard:
		state["nudges"] = nudges + 1
		return _payload_for_current(state, paper, "incomplete", "Not finished. Say 'Go on' and wait. Do not change question.")
	# A short answer is nudged once. If the learner says the same short thing again, take it: some
	# correct answers really are three words ("Learn Practice Doubt Test"), and looping on them
	# used to trap the learner until the clock ran out.
	if not _is_idk(heard) and _word_count(heard) < MIN_ANSWER_WORDS and nudges < 1:
		state["nudges"] = nudges + 1
		return _payload_for_current(state, paper, "incomplete", "Only a fragment so far. Say 'Go on' and wait.")
	_record(state, paper, transcript, metrics)
	thin = _is_idk(heard) or _word_count(heard) < 20
	if thin and not state.get("probe_used") and state.get("probes", 0) < MAX_SESSION_PROBES and not _is_idk(heard):
		state.update(probe_active=True, probe_used=True, probes=state.get("probes", 0) + 1, answered=False, asked_at=time.time())
		payload = _payload_for_current(state, paper, "", "Ask this follow-up once, then wait for a complete answer.")
		payload.update(ok=True, use_probe=True)
		return payload
	state.update(answered=True, probe_active=False)
	remaining = len(paper) - len(state["asked"])
	return {
		"ok": True,
		"allow_next_stem": True,
		"remaining_after_this": remaining,
		"instruction": "Answer recorded. Call get_next_stem and ask it." if remaining else "All questions done. Call finish_viva and close in one sentence.",
	}


def _next_stem(state, paper) -> dict[str, Any]:
	if state.get("current") is not None and not state.get("answered"):
		return _payload_for_current(state, paper, "awaiting_answer", "The learner has not finished. Re-ask THIS question only, then wait.")
	for idx, q in enumerate(paper):
		if idx not in state["asked"]:
			state["asked"].append(idx)
			state.update(current=idx, answered=False, probe_active=False, probe_used=False, nudges=0, asked_at=time.time())
			return {
				"question": q["stem"],
				"question_number": len(state["asked"]),
				"remaining_after_this": len(paper) - len(state["asked"]),
				"allow_next_stem": False,
				"instruction": "Ask only this question now and wait for a complete answer.",
			}
	state["done"] = True
	return {"error": "no_more_stems", "allow_next_stem": False, "instruction": "No questions left. Call finish_viva and close in one sentence."}


@frappe.whitelist(methods=["POST"])
def run_tool(attempt: str, name: str = "", args: Any = None, metrics: Any = None):
	"""Execute one of Asha's function calls. The paper stays here; she gets one question at a time."""
	doc = _own_attempt(attempt)
	if doc.status != "In Progress":
		return {"result": {"error": "closed", "instruction": "The viva has ended. Say goodbye in one sentence."}, "done": True}
	if isinstance(args, str):
		try:
			args = json.loads(args)
		except ValueError:
			args = {}
	args = args if isinstance(args, dict) else {}
	state, paper = _state(doc), _paper(doc)
	tool = (name or "").strip()
	if tool == "commit_answer":
		result = _commit_answer(state, paper, args, _clean_metrics(metrics))
	elif tool == "get_next_stem":
		result = _next_stem(state, paper)
	elif tool == "finish_viva":
		pending = len(paper) - len(state["asked"]) + (0 if state.get("answered") else 1)
		elapsed = (now_datetime() - get_datetime(doc.started_at)).total_seconds()
		if pending > 0 and elapsed < TIME_LIMIT_S:
			result = {"error": "stems_remaining", "allow_next_stem": bool(state.get("answered")), "instruction": "Questions remain. Continue the current one."}
		else:
			state["done"] = True
			result = {"ok": True}
	else:
		result = {"error": "unknown_tool"}
	_save_state(doc, state)
	frappe.db.commit()
	return {
		"result": result,
		"done": bool(state.get("done")),
		"question_number": len(state.get("asked") or []),
		"questions": len(paper),
	}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

FILLER_RE = re.compile(r"\b(um+|uh+|erm+|hmm+|like|basically|actually|you know|matlab)\b", re.I)

SCORE_SCHEMA = {
	"type": "OBJECT",
	"properties": {
		"answers": {
			"type": "ARRAY",
			"items": {
				"type": "OBJECT",
				"properties": {
					"index": {"type": "INTEGER"},
					"knowledge_score": {"type": "INTEGER"},
					"covered_points": {"type": "ARRAY", "items": {"type": "STRING"}},
					"missed_points": {"type": "ARRAY", "items": {"type": "STRING"}},
					"feedback": {"type": "STRING"},
				},
				"required": ["index", "knowledge_score", "covered_points", "missed_points", "feedback"],
			},
		},
		"summary": {"type": "STRING"},
		"strengths": {"type": "ARRAY", "items": {"type": "STRING"}},
		"improvements": {"type": "ARRAY", "items": {"type": "STRING"}},
	},
	"required": ["answers", "summary", "strengths", "improvements"],
}


def _fluency(turn: dict[str, Any]) -> tuple[float, list[str]]:
	"""Delivery score from timing alone. Hesitation lowers it and is flagged; it never fails anyone by itself."""
	flags = []
	if _is_idk(turn.get("answer") or "") or not (turn.get("answer") or "").strip():
		# Nothing was said: the delivery score can't reward a silence that the learner sat out.
		return 0.0, [_("No answer given")]
	think = turn["think_ms"] / 1000
	if think <= 4:
		score = 100.0
	elif think <= 10:
		score = 100 - (think - 4) * 3.3  # → 80
	elif think <= 30:
		score = 80 - (think - 10) * 1.5  # → 50
	elif think <= 60:
		score = 50 - (think - 30)  # → 20
	else:
		score = 15.0
	if think > 45:
		flags.append(_("Very long silence before answering ({0}s)").format(round(think)))
	elif think > 10:
		flags.append(_("Slow to start ({0}s)").format(round(think)))
	if turn["longest_pause_ms"] > 8000:
		score -= 15
		flags.append(_("Long pause mid-answer ({0}s)").format(round(turn["longest_pause_ms"] / 1000)))
	if turn["pause_count"] > 3:
		score -= 10
	words = _word_count(turn["answer"])
	minutes = max(turn["speech_ms"], 1) / 60000
	wpm = words / minutes if turn["speech_ms"] > 3000 else 0
	turn["words"], turn["wpm"] = words, round(wpm)
	if wpm and wpm < 70:
		score -= 10
	fillers = len(FILLER_RE.findall(turn["answer"] or ""))
	turn["fillers"] = fillers
	if words and fillers / words > 0.08:
		score -= 10
	if turn["tab_switches"]:
		score -= min(40, 20 * turn["tab_switches"])
		flags.append(_("Left the viva screen {0} time(s)").format(turn["tab_switches"]))
	return max(0.0, min(100.0, round(score, 1))), flags


def _score_with_model(doc, paper, turns) -> dict[str, Any]:
	items = []
	for i, t in enumerate(turns):
		q = paper[t["idx"]]
		items.append(
			f"[{i}] QUESTION: {q['stem']}\nFOLLOW-UP (if asked): {q.get('probe')}\nMODEL ANSWER: {q.get('model_answer')}\n"
			f"KEY POINTS: {'; '.join(q.get('key_points') or [])}\nLEARNER SAID: {t['answer'] or '(nothing)'}"
		)
	system = (
		"You grade a spoken sales-training viva. Transcripts come from speech recognition: ignore grammar, "
		"filler words and minor transcription errors; judge only whether the learner knows the facts and could "
		"handle the situation with a parent. knowledge_score 0-100 per answer: 90+ all key points correct and "
		"well explained, 70-89 mostly right, 40-69 partly right or vague, 1-39 mostly wrong, 0 no answer or "
		"'I don't know'. Penalise invented facts. Feedback is one or two sentences addressed to the learner ('You…'). "
		"Summary is two sentences for their Training Manager. Strengths and improvements: max 3 each, short."
	)
	return _generate_json(system, "\n\n".join(items), SCORE_SCHEMA, temperature=0.1)


def _fallback_knowledge(q: dict[str, Any], answer: str) -> float:
	"""Rough overlap score if the text model is unreachable; flagged so a trainer can re-score."""
	if not answer or _is_idk(answer):
		return 0.0
	said = set(re.findall(r"[a-z0-9]+", answer.lower()))
	points = q.get("key_points") or [q.get("model_answer") or ""]
	hits = 0
	for p in points:
		words = [w for w in re.findall(r"[a-z0-9]+", p.lower()) if len(w) > 3]
		if words and sum(w in said for w in words) / len(words) >= 0.4:
			hits += 1
	return round(100 * hits / max(1, len(points)), 1)


def _finalize(doc, state: dict[str, Any], reason: str = "finished"):
	# Claim the attempt in one statement: two tabs finishing at once, or a stale sweep landing
	# alongside "End viva", would otherwise both score it and the loser would fail to save.
	if doc.status == "In Progress":
		if frappe.db.get_value("Sales Viva Attempt", doc.name, "status", for_update=True) != "In Progress":
			return  # someone else is already scoring it
		frappe.db.set_value("Sales Viva Attempt", doc.name, "status", "Scoring", update_modified=False)
		doc.reload()
	paper = _paper(doc)
	turns = sorted(state.get("turns") or [], key=lambda t: t["idx"])
	doc.status = "Scoring"
	doc.ended_at = now_datetime()
	doc.duration_s = int((get_datetime(doc.ended_at) - get_datetime(doc.started_at)).total_seconds())
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	graded, error = {}, None
	if turns:
		try:
			result = _score_with_model(doc, paper, turns)
			graded = {cint(a.get("index")): a for a in result.get("answers") or []}
			doc.summary = result.get("summary")
			doc.strengths = "\n".join(result.get("strengths") or [])
			doc.improvements = "\n".join(result.get("improvements") or [])
		except Exception:
			error = frappe.get_traceback()
			frappe.log_error(title="CRT viva: scoring failed", message=error)

	doc.set("turns", [])
	all_flags, knowledge, fluency = [], [], []
	# A question the learner passed on ("No answer", "I don't know") is not an answered question.
	answered = {t["idx"] for t in turns if not _is_idk(t.get("answer") or "") and (t.get("answer") or "").strip()}
	for i, t in enumerate(turns):
		q = paper[t["idx"]]
		g = graded.get(i) or {}
		k = flt(g.get("knowledge_score")) if g else _fallback_knowledge(q, t["answer"])
		f, flags = _fluency(t)
		if _is_idk(t["answer"]):
			flags.append(_("Said they don't know"))
		knowledge.append(k)
		fluency.append(f)
		all_flags += [f"Q{t['idx'] + 1}: {x}" for x in flags]
		doc.append(
			"turns",
			{
				"question": q["stem"],
				"concept": q.get("concept"),
				"probe_asked": t.get("probe_asked"),
				"answer": t["answer"],
				"think_ms": t["think_ms"],
				"answer_ms": t["answer_ms"],
				"speech_ms": t["speech_ms"],
				"pause_count": t["pause_count"],
				"longest_pause_ms": t["longest_pause_ms"],
				"tab_switches": t["tab_switches"],
				"words": t.get("words"),
				"wpm": t.get("wpm"),
				"fillers": t.get("fillers"),
				"knowledge_score": k,
				"fluency_score": f,
				"feedback": g.get("feedback") or "",
				"covered_points": "\n".join(g.get("covered_points") or []),
				"missed_points": "\n".join(g.get("missed_points") or []),
				"watch_outs": "\n".join(flags),
			},
		)
	# Unanswered questions count as zero so running out the clock can't help.
	for idx, q in enumerate(paper):
		if idx not in answered:
			knowledge.append(0.0)
			fluency.append(0.0)
			doc.append("turns", {"question": q["stem"], "concept": q.get("concept"), "answer": "", "knowledge_score": 0, "fluency_score": 0, "watch_outs": _("Not answered")})
	n = max(1, len(paper))
	doc.knowledge_score = round(sum(knowledge) / n, 1)
	doc.fluency_score = round(sum(fluency) / n, 1)
	doc.overall_score = round(0.7 * doc.knowledge_score + 0.3 * doc.fluency_score, 1)
	if reason == "left":
		all_flags.append(_("Viva was not finished (left or lost connection)"))
	if error:
		all_flags.append(_("Knowledge scored automatically (AI grading unavailable) — trainer should review"))
		doc.scoring_error = error[-1000:]
	doc.watch_outs = "\n".join(all_flags)
	passed = doc.overall_score >= PASS_MARK and len(answered) >= n - 1
	doc.verdict = _("Ready") if passed and doc.overall_score >= READY_MARK else (_("Passed") if passed else _("Not yet"))
	doc.status = "Passed" if passed else "Not Passed"
	doc.live_state_json = json.dumps(state)
	doc.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist(methods=["POST"])
def finish_attempt(attempt: str, reason: str = "finished"):
	"""End the call and score it. Safe to call twice."""
	doc = _own_attempt(attempt)
	if doc.status == "In Progress":
		_finalize(doc, _state(doc), reason="left" if reason in ("left", "error") else "finished")
	return get_viva_report(doc.name)


# ---------------------------------------------------------------------------
# Reports, results list, unlocks
# ---------------------------------------------------------------------------


def _can_view(member: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	from lms.lms import access

	if user == member or access.is_super_admin(user):
		return True
	# A viva holds the learner's answers and the trainer's notes: staff see the people in their own
	# teams or reporting tree, not everyone with the same role.
	return access.can_view_member(member, user) or member in access.training_manager_tree(user)


def _can_unlock(member: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	from lms.lms import access

	if user == member:
		return False
	if access.is_super_admin(user):
		return True
	return access.can_manage_member(member, user) or member in access.training_manager_tree(user)


@frappe.whitelist()
def get_viva_report(attempt: str):
	user = _require_login()
	doc = frappe.get_doc("Sales Viva Attempt", attempt)
	if not _can_view(doc.member, user):
		frappe.throw(_("You can't see this viva."), frappe.PermissionError)
	course = doc.course or COURSE_SLUG
	state = day_viva_state(doc.member, course, doc.crt_number)
	from lms.lms.day_journey import day_slug
	return {
		"name": doc.name,
		"member": doc.member,
		"member_name": doc.member_name or frappe.db.get_value("User", doc.member, "full_name"),
		"crt_number": doc.crt_number,
		"day": doc.crt_number,
		"course": course,
		"course_title": course_title(course),
		"days_total": _day_count(course),
		"title": day_title(course, doc.crt_number),
		"slug": day_slug(doc.crt_number, day_title(course, doc.crt_number)),
		"attempt_no": doc.attempt_no,
		"status": doc.status,
		"started_at": doc.started_at,
		"duration_s": doc.duration_s,
		"overall_score": doc.overall_score,
		"knowledge_score": doc.knowledge_score,
		"fluency_score": doc.fluency_score,
		"verdict": doc.verdict,
		"summary": doc.summary,
		"strengths": [s for s in (doc.strengths or "").split("\n") if s],
		"improvements": [s for s in (doc.improvements or "").split("\n") if s],
		"flags": [s for s in (doc.watch_outs or "").split("\n") if s],
		"recording": bool(doc.get("recording")),
		"pass_mark": PASS_MARK,
		"is_own": doc.member == user,
		"can_unlock": _can_unlock(doc.member, user) and state["blocked"],
		"day_state": state,
		"turns": [
			{
				"question": t.question,
				"concept": t.concept,
				"answer": t.answer,
				"probe_asked": t.probe_asked,
				"think_ms": t.think_ms,
				"answer_ms": t.answer_ms,
				"speech_ms": t.speech_ms,
				"pause_count": t.pause_count,
				"longest_pause_ms": t.longest_pause_ms,
				"tab_switches": t.tab_switches,
				"words": t.words,
				"wpm": t.wpm,
				"knowledge_score": t.knowledge_score,
				"fluency_score": t.fluency_score,
				"feedback": t.feedback,
				"covered_points": [s for s in (t.covered_points or "").split("\n") if s],
				"missed_points": [s for s in (t.missed_points or "").split("\n") if s],
				"flags": [s for s in (t.watch_outs or "").split("\n") if s],
			}
			for t in doc.turns
		],
	}


@frappe.whitelist()
def get_viva_results(crt_number=None, status: str | None = None, search: str | None = None, course: str | None = None):
	"""Attempts of everyone the current user can see (staff: all; managers: their people)."""
	user = _require_login()
	from lms.lms import access

	filters: dict[str, Any] = {"status": ["in", ["Passed", "Not Passed", "Scoring"]]}
	if course:
		filters["course"] = course
	if cint(crt_number):
		filters["crt_number"] = cint(crt_number)
	if status in ("Passed", "Not Passed"):
		filters["status"] = status
	viva_courses = [
		{"name": c.name, "title": c.title}
		for c in frappe.get_all("LMS Course", {"day_viva": 1}, ["name", "title"], order_by="title")
	]
	empty = {"rows": [], "blocked": [], "configured": is_configured(), "courses": viva_courses}
	# Super Admins see every result; everyone else sees their own teams and reporting tree.
	scope = None if access.is_super_admin(user) else access.get_visible_members(user)
	if scope is not None:
		members = set(scope) | set(access.training_manager_tree(user))
		if not members:
			return empty
		filters["member"] = ["in", sorted(members)]
	rows = frappe.get_all(
		"Sales Viva Attempt",
		filters,
		["name", "member", "member_name", "course", "crt_number", "attempt_no", "status", "overall_score", "knowledge_score", "fluency_score", "verdict", "watch_outs", "started_at", "recording"],
		order_by="started_at desc",
		limit=500,
	)
	if search:
		needle = search.lower()
		rows = [r for r in rows if needle in (r.member_name or "").lower() or needle in r.member.lower()]
	titles = {c["name"]: c["title"] for c in viva_courses}
	for r in rows:
		r.course = r.course or COURSE_SLUG
		r.course_title = titles.get(r.course) or course_title(r.course)
		r.flag_count = len([f for f in (r.watch_outs or "").split("\n") if f])
		r.recording = bool(r.recording)  # a flag, never the private file path
	blocked = []
	for member, crs, day in {(r.member, r.course, r.crt_number) for r in rows if r.status == "Not Passed"}:
		st = day_viva_state(member, crs, day)
		if st["blocked"]:
			blocked.append(
				{
					"member": member,
					"member_name": next(r.member_name for r in rows if r.member == member),
					"course": crs,
					"course_title": titles.get(crs) or course_title(crs),
					"crt_number": day,
					"day": day,
					"attempts_used": st["attempts_used"],
					"best_score": st["best_score"],
					"can_unlock": _can_unlock(member, user),
				}
			)
	return {
		**empty,
		"rows": rows,
		"blocked": sorted(blocked, key=lambda b: (b["member_name"] or "", b["course"], b["day"])),
	}


@frappe.whitelist(methods=["POST"])
def grant_attempts(member: str, crt_number=None, reason: str = "", course: str | None = None, day=None):
	"""Training Manager (or staff) gives a learner three more attempts after they used theirs."""
	user = _require_login()
	course, day = _course_day(course, day, crt_number)
	if not _can_unlock(member, user):
		frappe.throw(_("Only this learner's Training Manager or an admin can unlock attempts."), frappe.PermissionError)
	frappe.get_doc(
		{
			"doctype": "Sales Viva Unlock",
			"member": member,
			"course": course,
			"crt_number": day,
			"chapter": day_chapter(course, day),
			"extra_attempts": ATTEMPTS_PER_DAY,
			"granted_by": user,
			"reason": (reason or "")[:500],
		}
	).insert(ignore_permissions=True)
	return day_viva_state(member, course, day)


@frappe.whitelist()
def viva_status():
	"""Whether the voice viva is switched on (never exposes the key)."""
	_require_login()
	return {"configured": is_configured(), "model": live_model()}


def repair_legacy_records():
	"""after_migrate: fix rows written before the course field and the watch_outs rename existed.

	Unlocks granted before vivas became multi-course have no course, so `attempts_allowed` (which
	filters by course) ignored them and those learners were blocked again. Attempts written before
	the `flags` field was renamed kept their watch-outs in the old column.
	"""
	if frappe.db.exists("DocType", "Sales Viva Unlock") and frappe.db.has_column("Sales Viva Unlock", "course"):
		orphaned = frappe.get_all("Sales Viva Unlock", filters={"course": ["in", ["", None]]}, pluck="name")
		for name in orphaned:
			frappe.db.set_value("Sales Viva Unlock", name, "course", COURSE_SLUG, update_modified=False)
		if orphaned:
			print(f"sales_viva: restored the course on {len(orphaned)} unlock(s)")
	for doctype in ("Sales Viva Attempt", "Sales Viva Unlock"):
		if not frappe.db.has_column(doctype, "chapter"):
			continue
		for row in frappe.get_all(doctype, {"chapter": ["in", ["", None]]}, ["name", "course", "crt_number"]):
			chapter = day_chapter(row.course or COURSE_SLUG, row.crt_number)
			if chapter:
				frappe.db.set_value(doctype, row.name, "chapter", chapter, update_modified=False)
	if frappe.db.has_column("Sales Viva Attempt", "flags") and frappe.db.has_column(
		"Sales Viva Attempt", "watch_outs"
	):
		frappe.db.sql(
			"""update `tabSales Viva Attempt` set watch_outs = flags
			where ifnull(watch_outs, '') = '' and ifnull(flags, '') != ''"""
		)


# ---------------------------------------------------------------------------
# Recording — what was actually said
# ---------------------------------------------------------------------------

RECORDING_MAX_BYTES = 25 * 1024 * 1024
RECORDING_TYPES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/mpeg": ".mp3"}


@frappe.whitelist(methods=["POST"])
def save_recording(attempt: str):
	"""Store the call audio against an attempt.

	The scoring model can be wrong; the recording is the record of what was actually said, so a
	Training Manager can listen for themselves. Only the learner's own browser uploads it, once.
	"""
	user = _require_login()
	doc = frappe.get_doc("Sales Viva Attempt", attempt)
	if doc.member != user:
		frappe.throw(_("Only the learner's own viva can be uploaded."), frappe.PermissionError)
	if doc.get("recording"):
		return {"saved": True, "already": True}
	uploaded = (frappe.request.files or {}).get("file") if frappe.request else None
	if not uploaded:
		frappe.throw(_("No audio was received."))
	content = uploaded.stream.read()
	if not content:
		frappe.throw(_("The recording was empty."))
	if len(content) > RECORDING_MAX_BYTES:
		frappe.throw(_("That recording is too long to store."))
	extension = RECORDING_TYPES.get((uploaded.mimetype or "").split(";")[0].strip(), ".webm")
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"viva-{doc.name}{extension}",
			"attached_to_doctype": "Sales Viva Attempt",
			"attached_to_name": doc.name,
			"attached_to_field": "recording",
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)
	doc.db_set("recording", file_doc.file_url, update_modified=False)
	return {"saved": True, "seconds": cint(doc.duration_s)}


@frappe.whitelist()
def get_recording(attempt: str):
	"""Serve the audio to the learner, their manager or an admin — never as a public URL."""
	user = _require_login()
	doc = frappe.get_doc("Sales Viva Attempt", attempt)
	if not _can_view(doc.member, user):
		frappe.throw(_("You can't listen to this viva."), frappe.PermissionError)
	url = doc.get("recording")
	if not url:
		frappe.throw(_("This viva has no recording."), frappe.DoesNotExistError)
	name = frappe.db.get_value("File", {"file_url": url, "attached_to_name": doc.name}, "name")
	if not name:
		frappe.throw(_("This recording is no longer stored."), frappe.DoesNotExistError)
	file_doc = frappe.get_doc("File", name)
	frappe.local.response.filename = file_doc.file_name
	frappe.local.response.filecontent = file_doc.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"
