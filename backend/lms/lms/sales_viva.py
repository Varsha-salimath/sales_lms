# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""CRT viva — Gemini Live native audio (speech-to-speech).

Examiner: Gemini Live Bidirectional API (BidiGenerateContent).
Model: gemini-3.8-live

The browser never sees GEMINI_API_KEY. Frappe mints a short-lived
ephemeral token; the learner's mic streams PCM to Gemini Live while they
speak, and Asha replies as native audio. Sarvam is not used.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import frappe
from frappe import _

GEMINI_LIVE_MODEL = "gemini-3.8-live"
GEMINI_VOICE = "Kore"
GEMINI_AUTH_TOKENS_URL = "https://generativelanguage.googleapis.com/v1alpha/auth_tokens"
GEMINI_LIVE_WS = (
	"wss://generativelanguage.googleapis.com/ws/"
	"google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained"
)
KEY_ENV_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY")

SESSION_TTL_S = 20 * 60
CACHE_PREFIX = "crt_viva:"
MAX_TEXT_CHARS = 2500
TOKEN_TIMEOUT_S = 20
STEMS_PER_VIVA = 5
MIN_ANSWER_WORDS = 8
MAX_SESSION_PROBES = 2

BANK: list[dict[str, Any]] = [
	{
		"id": "pf1",
		"concept": "Product foundation",
		"stem": "What is Infinity Learn, and how is it different from a typical tuition centre?",
		"probe": "Then tell me who the Academic Counsellor is selling to — the child, or the parent — and why that matters on Day 1.",
		"keywords": ["infinity learn", "sri chaitanya", "online", "counsellor", "parent", "k12", "foundation", "programme"],
		"model": "Infinity Learn is Sri Chaitanya’s online K-12 programmes. Counsellor sells to the parent, not a tuition-centre walk-in.",
	},
	{
		"id": "il1",
		"concept": "Infinity Learn products",
		"stem": "Name the main Infinity Learn programmes you would offer a Class 10 parent, and when you choose Foundation versus Test Prep.",
		"probe": "A parent says the child is weak in boards but wants JEE later. Which programme do you open with, and why?",
		"keywords": ["foundation", "test prep", "math champ", "board", "jee", "neet", "class", "programme"],
		"model": "Foundation for board gaps and concepts; Test Prep when the target exam is clear (JEE/NEET).",
	},
	{
		"id": "cf1",
		"concept": "Call flow",
		"stem": "Walk me through the opening of a parent call after a lead comes in. What do you confirm before you pitch?",
		"probe": "If the parent sounds rushed, what do you still confirm before you talk product?",
		"keywords": ["introduce", "rapport", "name", "class", "board", "need", "discovery", "child", "confirm"],
		"model": "Introduce self and Infinity Learn, confirm child name/class/board, discover need, then pitch.",
	},
	{
		"id": "lsq1",
		"concept": "LSQ",
		"stem": "A parent says call after the PTM. Which LSQ disposition do you log, and what next action do you book?",
		"probe": "What breaks if you end the call without a next action in LSQ?",
		"keywords": ["lsq", "disposition", "callback", "follow", "ptm", "next action", "date", "pipeline"],
		"model": "Log a callback / follow-up disposition, book the PTM-dated next action, do not leave LSQ empty.",
	},
	{
		"id": "pitch1",
		"concept": "Pitch",
		"stem": "Give me a thirty-second pitch for Infinity Learn Foundation to a parent who thinks school is enough.",
		"probe": "Which proof point do you use if they still say the school teacher is enough?",
		"keywords": ["school", "foundation", "gap", "board", "practice", "demo", "counsellor", "concept"],
		"model": "School covers syllabus; Foundation closes gaps with structured practice and a counsellor demo.",
	},
	{
		"id": "obj1",
		"concept": "Objections",
		"stem": "The parent says we will think about it. How do you handle that without sounding pushy?",
		"probe": "What next step do you lock before you hang up?",
		"keywords": ["think", "concern", "demo", "trial", "timeline", "next", "callback", "objection"],
		"model": "Isolate the real concern, offer a demo or callback with a date, never dump more product.",
	},
	{
		"id": "mc1",
		"concept": "Infinity Learn products",
		"stem": "What is Math Champ, and which parent profile is it for?",
		"probe": "If the child avoids homework because they fear maths, do you pitch Test Prep or Math Champ first?",
		"keywords": ["math", "champ", "fear", "homework", "practice", "foundation", "weak"],
		"model": "Math Champ is for maths fear / homework avoidance — not a JEE Test Prep open.",
	},
	{
		"id": "lsq2",
		"concept": "LSQ / call flow",
		"stem": "Why do we capture board, class, and next action in LSQ before ending the call?",
		"probe": "Give me one example of a bad disposition after a live parent call.",
		"keywords": ["lsq", "board", "class", "next action", "disposition", "follow", "pipeline"],
		"model": "LSQ is the pipeline of record. Missing board/class/next action means the next counsellor cannot continue.",
	},
]

LIVE_TOOLS = [
	{
		"functionDeclarations": [
			{
				"name": "commit_answer",
				"behavior": "BLOCKING",
				"description": (
					"Call only when the learner finished a complete answer to the CURRENT stem "
					"(a full thought, several sentences, or 'I don't know'). "
					"Never call this on a mid-sentence pause or after the first clause."
				),
				"parameters": {
					"type": "OBJECT",
					"properties": {
						"transcript": {
							"type": "STRING",
							"description": "What you heard, as complete as possible.",
						},
						"complete": {
							"type": "BOOLEAN",
							"description": "True only if they finished the thought.",
						},
					},
					"required": ["complete"],
				},
			},
			{
				"name": "get_next_stem",
				"behavior": "BLOCKING",
				"description": (
					"Return the next unseen CRT Day 1 stem. Call only after commit_answer "
					"returned allow_next_stem true, or at the very start of the viva. "
					"Never invent a stem. If the tool says awaiting_answer, stay on that stem."
				),
				"parameters": {
					"type": "OBJECT",
					"properties": {
						"reason": {"type": "STRING", "description": "Why you need the next stem."},
					},
				},
			},
			{
				"name": "finish_viva",
				"behavior": "BLOCKING",
				"description": (
					"Call when five stems are done or the learner is out of time. "
					"Then speak one closing sentence. Do not grade out loud."
				),
				"parameters": {
					"type": "OBJECT",
					"properties": {
						"reason": {"type": "STRING"},
					},
				},
			},
		]
	}
]


def _gemini_key_name() -> str:
	for name in KEY_ENV_NAMES:
		raw = (os.environ.get(name) or "").strip().strip('"').strip("'")
		if raw:
			return name
	return "GEMINI_API_KEY"


def _gemini_key() -> str:
	for name in KEY_ENV_NAMES:
		raw = (os.environ.get(name) or "").strip().strip('"').strip("'")
		if raw:
			return raw
	return ""


def _assert_key() -> str:
	key = _gemini_key()
	if not key:
		frappe.throw(
			_("Add GEMINI_API_KEY — this demo uses Gemini Live, not Chrome speech."),
			frappe.ValidationError,
		)
	return key


def _gemini_error_message(body: bytes, status: int) -> str:
	try:
		parsed = json.loads(body.decode("utf-8", errors="replace"))
	except ValueError:
		return _("Gemini request failed ({0}).").format(status)
	err = parsed.get("error") if isinstance(parsed, dict) else None
	if isinstance(err, dict):
		msg = err.get("message") or err.get("status")
		if msg:
			return str(msg)
	if isinstance(parsed, dict) and parsed.get("message"):
		return str(parsed["message"])
	return _("Gemini request failed ({0}).").format(status)


def _gemini_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
	key = _assert_key()
	req = Request(
		url,
		data=json.dumps(payload).encode("utf-8"),
		method="POST",
		headers={
			"x-goog-api-key": key,
			"Content-Type": "application/json",
		},
	)
	try:
		with urlopen(req, timeout=TOKEN_TIMEOUT_S) as resp:
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
	if not isinstance(parsed, dict):
		frappe.throw(_("Gemini returned an unexpected payload."), frappe.ValidationError)
	return parsed


def _mulberry32(seed: int):
	state = seed & 0xFFFFFFFF

	def rng() -> float:
		nonlocal state
		state = (state + 0x6D2B79F5) & 0xFFFFFFFF
		t = state
		t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
		t ^= (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)) & 0xFFFFFFFF
		return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

	return rng


def _hash_seed(s: str) -> int:
	h = 2166136261
	for ch in s:
		h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
	return h


def _pick_paper(seed: str) -> list[dict[str, Any]]:
	rng = _mulberry32(_hash_seed(seed))
	copy = list(BANK)
	for i in range(len(copy) - 1, 0, -1):
		j = int(rng() * (i + 1))
		copy[i], copy[j] = copy[j], copy[i]
	seen: set[str] = set()
	out: list[dict[str, Any]] = []
	for q in copy:
		if q["concept"] in seen and len(out) + (len(copy) - copy.index(q)) > 5:
			continue
		out.append(q)
		seen.add(q["concept"])
		if len(out) == STEMS_PER_VIVA:
			break
	i = 0
	while len(out) < STEMS_PER_VIVA:
		out.append(copy[i % len(copy)])
		i += 1
	return out[:STEMS_PER_VIVA]


def _asha_system(session: dict[str, Any]) -> str:
	stems = []
	for i, q in enumerate(session["paper"], start=1):
		stems.append(f"{i}. [{q['id']}] {q['concept']}: {q['stem']} | probe: {q['probe']}")
	bank = "\n".join(stems)
	return (
		"You are Asha, a CRT faculty examiner speaking out loud. This is a viva, not a chatbot and not tutoring.\n"
		"Speak short spoken English the learner will hear. Indian faculty tone. Firm, fair, brief.\n"
		"Learners think out loud. They pause, restart, and finish a thought slowly. That is normal.\n"
		"Turn-taking (do not break this):\n"
		"- A pause is NOT the end of an answer. Do not jump to the next question mid-answer.\n"
		"- Stay on the current stem until commit_answer returns allow_next_stem true.\n"
		"- If a tool returns awaiting_answer, incomplete, or the same stem again, you jumped too early. "
		"Say 'Go on' or 'Take your time', then wait. Do not invent a new question.\n"
		"- Call commit_answer only after a complete thought (several sentences or 'I don't know'), never after the first clause.\n"
		"- Call get_next_stem only at the start, or after allow_next_stem is true.\n"
		"- If you already started a new question by mistake, stop and re-ask the CURRENT stem from the tool payload.\n"
		"Rules:\n"
		"- Ask only stems returned by get_next_stem. Never invent a question or product fact.\n"
		"- Never answer for the learner. Never hint, teach, or complete their answer.\n"
		"- One short acknowledgement after a solid complete answer, then the next stem.\n"
		"- If commit_answer returns a probe, ask that probe once and wait for a full answer. Max two probes in the whole viva.\n"
		"- Accept Hinglish and 'I don't know' without comment.\n"
		"- After five stems, call finish_viva and close in one sentence. Do not read scores aloud.\n"
		"- Do not small-talk. Do not leave the Day 1 CRT bank.\n"
		f"Unique paper {session['seed']}. Today's CRT Day 1 stems (context only — still call the tool):\n"
		f"{bank}"
	)


def _live_setup(session: dict[str, Any]) -> dict[str, Any]:
	return {
		"model": f"models/{GEMINI_LIVE_MODEL}",
		"generationConfig": {
			"responseModalities": ["AUDIO"],
			"temperature": 0.3,
			"speechConfig": {
				"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": GEMINI_VOICE}},
				"languageCode": "en-IN",
			},
		},
		"systemInstruction": {"parts": [{"text": _asha_system(session)}]},
		"tools": LIVE_TOOLS,
		"realtimeInputConfig": {
			"automaticActivityDetection": {"disabled": True},
			"activityHandling": "START_OF_ACTIVITY_INTERRUPTS",
			"turnCoverage": "TURN_INCLUDES_ONLY_ACTIVITY",
		},
		"inputAudioTranscription": {"languageCode": "en-IN"},
		"outputAudioTranscription": {"languageCode": "en-IN"},
		"sessionResumption": {},
	}


def _cache_key(session_id: str) -> str:
	return CACHE_PREFIX + session_id


def _save_session(session: dict[str, Any]) -> None:
	frappe.cache().set_value(_cache_key(session["id"]), session, expires_in_sec=SESSION_TTL_S)


def _load_session(session_id: str) -> dict[str, Any]:
	sid = (session_id or "").strip()
	if not sid:
		frappe.throw(_("Missing viva session."), frappe.ValidationError)
	session = frappe.cache().get_value(_cache_key(sid))
	if not session or not isinstance(session, dict):
		frappe.throw(_("Viva session expired. Start again."), frappe.ValidationError)
	return session


def _word_count(text: str) -> int:
	return len([w for w in (text or "").strip().split() if w])


def _is_idk(text: str) -> bool:
	t = (text or "").lower().replace("’", "'")
	return bool(re.search(r"\b(i don't know|i dont know|no idea|skip this)\b", t))


def _current_stem_payload(session: dict[str, Any], error: str, instruction: str) -> dict[str, Any]:
	q = session.get("current_q") or {}
	asked = session.get("asked_ids") or []
	return {
		"error": error,
		"instruction": instruction,
		"allow_next_stem": False,
		"id": q.get("id") or "",
		"concept": q.get("concept") or "",
		"stem": q.get("stem") or "",
		"probe": q.get("probe") or "",
		"probe_active": bool(session.get("probe_active")),
		"asked_count": len(asked),
		"remaining_after_this": max(0, STEMS_PER_VIVA - len(asked)),
	}


def _has_complete_answer(session: dict[str, Any]) -> bool:
	if not session.get("current_q"):
		return True
	return bool(session.get("current_answered"))


def _advance_stem(session: dict[str, Any]) -> dict[str, Any]:
	asked = session.setdefault("asked_ids", [])
	for q in session["paper"]:
		if q["id"] not in asked:
			asked.append(q["id"])
			session["current_q"] = q
			session["current_answered"] = False
			session["probe_active"] = False
			session["probe_used_for_current"] = False
			return {
				"id": q["id"],
				"concept": q["concept"],
				"stem": q["stem"],
				"probe": q["probe"],
				"asked_count": len(asked),
				"remaining_after_this": max(0, STEMS_PER_VIVA - len(asked)),
				"allow_next_stem": False,
				"instruction": (
					"Ask only this stem now. Wait for a complete answer. "
					"Do not call get_next_stem until commit_answer returns allow_next_stem true."
				),
			}
	session["done"] = True
	session["current_answered"] = True
	return {
		"error": "no_more_stems",
		"asked_count": len(asked),
		"remaining_after_this": 0,
		"allow_next_stem": False,
		"instruction": "No stems left. Call finish_viva and close in one sentence.",
	}


def _commit_answer(session: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
	q = session.get("current_q")
	if not q:
		return {
			"error": "no_current_stem",
			"allow_next_stem": False,
			"instruction": "Call get_next_stem first, then ask that stem.",
		}
	complete = args.get("complete")
	if isinstance(complete, str):
		complete = complete.strip().lower() in ("1", "true", "yes")
	transcript = str(args.get("transcript") or "").strip()
	if not complete:
		return _current_stem_payload(
			session,
			"incomplete",
			"Not finished. Stay on this stem. Say 'Go on' and wait. Do not ask a new question.",
		)
	if transcript and not (_is_idk(transcript) or _word_count(transcript) >= MIN_ANSWER_WORDS):
		return _current_stem_payload(
			session,
			"incomplete",
			"That was only a fragment. Stay on this stem. Say 'Go on' and wait.",
		)
	if not transcript:
		return _current_stem_payload(
			session,
			"incomplete",
			"No complete answer yet. Stay on this stem and wait.",
		)
	_record_turn(session, transcript[:MAX_TEXT_CHARS])
	turns = session.get("turns") or []
	last = next((t for t in reversed(turns) if t.get("id") == q["id"]), {})
	verdict = last.get("verdict") or "partial"
	probes = int(session.get("probes_used") or 0)
	can_probe = (
		verdict in ("partial", "wrong", "unknown")
		and not session.get("probe_used_for_current")
		and probes < MAX_SESSION_PROBES
	)
	if can_probe:
		session["probe_active"] = True
		session["probe_used_for_current"] = True
		session["probes_used"] = probes + 1
		session["current_answered"] = False
		payload = _current_stem_payload(
			session,
			"",
			"Ask this stem's probe once, then wait for a complete answer. Do not call get_next_stem yet.",
		)
		payload.pop("error", None)
		payload["ok"] = True
		payload["verdict"] = verdict
		payload["allow_next_stem"] = False
		payload["use_probe"] = True
		return payload
	session["current_answered"] = True
	session["probe_active"] = False
	remaining = max(0, STEMS_PER_VIVA - len(session.get("asked_ids") or []))
	instruction = (
		"Answer complete. Call get_next_stem and ask only that new stem."
		if remaining
		else "All five stems are done. Call finish_viva and close in one sentence."
	)
	return {
		"ok": True,
		"verdict": verdict,
		"allow_next_stem": True,
		"asked_count": len(session.get("asked_ids") or []),
		"remaining_after_this": remaining,
		"instruction": instruction,
	}


def _run_tool(session: dict[str, Any], name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
	args = args or {}
	if name == "commit_answer":
		return _commit_answer(session, args)
	if name == "get_next_stem":
		if session.get("current_q") and not _has_complete_answer(session):
			return _current_stem_payload(
				session,
				"awaiting_answer",
				"The learner has not finished this stem. Do not change question. "
				"Say 'Go on' or re-ask THIS stem only, then wait.",
			)
		return _advance_stem(session)
	if name == "finish_viva":
		asked = session.get("asked_ids") or []
		if (len(asked) < STEMS_PER_VIVA or not _has_complete_answer(session)) and not session.get("time_up"):
			return {
				"error": "stems_remaining",
				"asked_count": len(asked),
				"remaining_after_this": max(0, STEMS_PER_VIVA - len(asked)),
				"allow_next_stem": _has_complete_answer(session),
				"instruction": "Stems remain. Stay on the current stem until it is complete, then call get_next_stem. Do not close yet.",
			}
		session["done"] = True
		return {"ok": True, "asked_count": len(asked)}
	return {"error": "unknown_tool"}


def _score_answer(q: dict[str, Any], text: str) -> dict[str, Any]:
	t = (text or "").lower().replace("’", "'")
	words = [w for w in t.strip().split() if w]
	if _is_idk(t) or not words:
		return {"score": 0, "verdict": "unknown", "hits": 0}
	hits = sum(1 for k in q.get("keywords") or [] if k in t)
	ratio = hits / max(1, len(q.get("keywords") or []))
	score = round(30 + ratio * 70)
	if len(words) < 10:
		score = min(score, 45)
	if len(words) >= 18 and ratio >= 0.25:
		score = min(100, score + 8)
	verdict = "correct"
	if score < 40:
		verdict = "wrong"
	elif score < 70:
		verdict = "partial"
	return {"score": max(0, min(100, score)), "verdict": verdict, "hits": hits}


def _record_turn(session: dict[str, Any], text: str) -> None:
	q = session.get("current_q")
	if not q:
		return
	scored = _score_answer(q, text)
	session.setdefault("turns", []).append(
		{
			"id": q["id"],
			"concept": q["concept"],
			"stem": q["probe"] if session.get("probe_active") else q["stem"],
			"probe": bool(session.get("probe_active")),
			"answer": text,
			"via": "speech",
			"score": scored["score"],
			"verdict": scored["verdict"],
		}
	)
	session["spoken_turns"] = int(session.get("spoken_turns") or 0) + 1


def _result(session: dict[str, Any]) -> dict[str, Any]:
	turns = session.get("turns") or []
	by_concept: dict[str, list[int]] = {}
	for t in turns:
		by_concept.setdefault(t["concept"], []).append(int(t.get("score") or 0))
	concept_avg = [
		{"concept": c, "avg": round(sum(v) / len(v))}
		for c, v in by_concept.items()
		if v
	]
	overall = round(sum(c["avg"] for c in concept_avg) / len(concept_avg)) if concept_avg else 0
	strengths = [c["concept"] for c in concept_avg if c["avg"] >= 70]
	weaks = [c["concept"] for c in concept_avg if c["avg"] < 70]
	verdict = "Ready" if overall >= 80 else "Pass" if overall >= 60 else "Not yet"
	elapsed = max(0, int(time.time() - (session.get("started_at") or time.time())))
	return {
		"persona": "Asha",
		"day": 1,
		"session_seed": session["seed"],
		"unique_paper": True,
		"score": overall,
		"verdict": verdict,
		"pass": overall >= 60,
		"ready": overall >= 80,
		"strengths": strengths,
		"weak_concepts": weaks,
		"voice_does_not_mark": True,
		"engine": GEMINI_LIVE_MODEL,
		"s2s": True,
		"path": "gemini-live-bidi",
		"anti_cheat": {
			"randomised_stems": [q["id"] for q in session.get("paper") or []],
			"speech_turns": session.get("spoken_turns") or 0,
			"typed_turns": 0,
			"paste_blocked": True,
			"time_s": elapsed,
		},
		"turns": turns,
		"note": "Heuristic demo grader. Production: async JSON grader. Voice never marks.",
	}


def _mint_live_token(setup: dict[str, Any]) -> str:
	now = datetime.now(timezone.utc)
	payload = {
		"uses": 4,
		"expireTime": (now + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
		"newSessionExpireTime": (now + timedelta(minutes=12)).strftime("%Y-%m-%dT%H:%M:%SZ"),
		"bidiGenerateContentSetup": setup,
	}
	parsed = _gemini_json(GEMINI_AUTH_TOKENS_URL, payload)
	name = (parsed.get("name") or "").strip()
	if not name:
		frappe.throw(_("Gemini did not issue a Live ephemeral token."), frappe.ValidationError)
	return name


def _status_payload() -> dict[str, Any]:
	return {
		"configured": bool(_gemini_key()),
		"engine": GEMINI_LIVE_MODEL,
		"model": GEMINI_LIVE_MODEL,
		"voice": GEMINI_VOICE,
		"s2s": True,
		"path": "gemini-live-bidi",
		"env_var": _gemini_key_name() if _gemini_key() else "GEMINI_API_KEY",
		"voice_in": "gemini-live-pcm16-16k",
		"voice_out": "gemini-live-pcm16-24k",
		"csrf_token": frappe.sessions.get_csrf_token(),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def gemini_status() -> dict[str, Any]:
	"""Boolean only — never returns the key."""
	return _status_payload()


@frappe.whitelist(allow_guest=True, methods=["GET"])
def sarvam_status() -> dict[str, Any]:
	"""Compatibility alias. Sarvam is set aside; configured follows GEMINI_API_KEY."""
	payload = _status_payload()
	payload["legacy_note"] = "Sarvam set aside. Viva uses Gemini Live native audio."
	return payload


@frappe.whitelist(allow_guest=True, methods=["POST"])
def start_session() -> dict[str, Any]:
	"""Mint a unique paper and a Gemini Live ephemeral token. Key never leaves the server."""
	_assert_key()
	seed = "CRT-D1-" + secrets.token_hex(2).upper()
	session_id = uuid.uuid4().hex
	session: dict[str, Any] = {
		"id": session_id,
		"seed": seed,
		"paper": _pick_paper(seed),
		"asked_ids": [],
		"current_q": None,
		"current_answered": True,
		"probe_active": False,
		"probe_used_for_current": False,
		"probes_used": 0,
		"turns": [],
		"spoken_turns": 0,
		"done": False,
		"time_up": False,
		"started_at": time.time(),
	}
	setup = _live_setup(session)
	token = _mint_live_token(setup)
	_save_session(session)
	return {
		"session_id": session_id,
		"seed": seed,
		"asked_count": 0,
		"concept": "",
		"model": GEMINI_LIVE_MODEL,
		"voice": GEMINI_VOICE,
		"s2s": True,
		"path": "gemini-live-bidi",
		"ws_url": GEMINI_LIVE_WS + "?access_token=" + quote(token, safe=""),
		"setup": setup,
		"engine": GEMINI_LIVE_MODEL,
	}


def _tool_args(raw: Any) -> dict[str, Any]:
	if isinstance(raw, dict):
		return raw
	if isinstance(raw, str) and raw.strip():
		try:
			parsed = json.loads(raw)
		except ValueError:
			return {}
		return parsed if isinstance(parsed, dict) else {}
	return {}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def run_tool(session_id: str = "", name: str = "", args: Any = None) -> dict[str, Any]:
	"""Execute a Live function call on the server (stems stay in Frappe)."""
	session = _load_session(session_id)
	tool = (name or "").strip()
	result = _run_tool(session, tool, _tool_args(args))
	_save_session(session)
	q = session.get("current_q") or {}
	return {
		"result": result,
		"done": bool(session.get("done")),
		"asked_count": len(session.get("asked_ids") or []),
		"concept": q.get("concept") or "",
		"session_id": session["id"],
		"seed": session["seed"],
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def record_answer(session_id: str = "", transcript: str = "") -> dict[str, Any]:
	"""Store a spoken turn transcript for the rubric. Does not call Gemini."""
	session = _load_session(session_id)
	text = (transcript or "").strip()
	if text and (_is_idk(text) or _word_count(text) >= 4):
		_record_turn(session, text[:MAX_TEXT_CHARS])
		_save_session(session)
	q = session.get("current_q") or {}
	return {
		"ok": True,
		"asked_count": len(session.get("asked_ids") or []),
		"concept": q.get("concept") or "",
		"spoken_turns": session.get("spoken_turns") or 0,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def session_result(session_id: str = "") -> dict[str, Any]:
	"""Return the heuristic score JSON after finish_viva."""
	session = _load_session(session_id)
	session["done"] = True
	_save_session(session)
	return _result(session)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_turn(session_id: str = "", transcript: str = "", event: str = "") -> dict[str, Any]:
	"""Control events only (idk / time_up). Speech itself goes through Gemini Live."""
	session = _load_session(session_id)
	kind = (event or "").strip().lower()
	text = (transcript or "").strip()
	if kind == "idk":
		_record_turn(session, "I don't know.")
		session["probe_active"] = False
	elif kind == "time_up":
		session["time_up"] = True
		session["done"] = True
	elif text:
		_record_turn(session, text)
	_save_session(session)
	q = session.get("current_q") or {}
	return {
		"ok": True,
		"done": bool(session.get("done")),
		"asked_count": len(session.get("asked_ids") or []),
		"concept": q.get("concept") or "",
		"inject": (
			"Time is up. Call finish_viva and close in one sentence."
			if kind == "time_up"
			else "I don't know."
			if kind == "idk"
			else "Please repeat only the last question. Do not teach or add a hint."
			if kind == "repeat"
			else ""
		),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_audio(session_id: str = "") -> dict[str, Any]:
	"""Disabled — viva is Gemini Live S2S, not blob-after-silence STT."""
	frappe.throw(_("This viva streams to Gemini Live. Hard-refresh /viva."), frappe.ValidationError)
	return {"session_id": session_id}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sarvam_stt() -> dict[str, Any]:
	"""Disabled — Sarvam set aside."""
	frappe.throw(_("Sarvam STT is disabled. Viva uses Gemini Live."), frappe.ValidationError)
	return {}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sarvam_tts(text: str = "") -> dict[str, Any]:
	"""Disabled — Sarvam set aside."""
	frappe.throw(_("Sarvam TTS is disabled. Viva uses Gemini Live."), frappe.ValidationError)
	return {"text": text}
