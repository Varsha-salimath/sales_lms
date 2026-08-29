# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Scripted Sales OJT simulations scored against the CRT Audit Sample rubric."""

from __future__ import annotations

import json
import re

import frappe
from frappe.utils import cint, now_datetime

# Excel Audit Sample columns — the official CRT call-audit rubric.
AUDIT_CRITERIA = [
	"Introduction",
	"Rapport Building",
	"Need Generation",
	"Session Pitching",
	"Closing",
]

SCENARIOS = [
	{
		"scenario_key": "demo-booking-call",
		"title": "Demo booking call",
		"source_crt": "CRT 2",
		"customer_name": "Mrs. Sharma",
		"customer_role": "Parent — Class 10",
		"objective": "Open the call correctly, understand the child’s exam goal, and book a counsellor demo.",
		"context": (
			"You are an Academic Counsellor at Infinity Learn. Mrs. Sharma’s number came from a "
			"website lead. Her daughter is in Class 10 and she is unsure whether Foundation or "
			"Test Prep is the right next step. Follow the CRT Day 2 call flow."
		),
		"instructions": (
			"Introduce yourself and Infinity Learn, build rapport, ask discovery questions, "
			"pitch a relevant program, handle one hesitation, and close by booking a demo."
		),
		"sort_order": 1,
		"beats": [
			{
				"key": "open",
				"customer": "Hello? Who is this?",
				"hint": "Introduce yourself, the company, and why you are calling.",
				"keywords": ["infinity", "counsellor", "counselor", "academic", "calling", "myself"],
				"criterion": "Introduction",
			},
			{
				"key": "rapport",
				"customer": "Okay… I have two minutes. What is this about?",
				"hint": "Acknowledge her time, ask about her daughter, and build comfort.",
				"keywords": ["daughter", "class", "how is", "time", "understand", "help"],
				"criterion": "Rapport Building",
			},
			{
				"key": "need",
				"customer": "She is in 10th. Boards are coming and we are confused about JEE later.",
				"hint": "Generate need — boards vs JEE, current coaching, gaps.",
				"keywords": ["board", "jee", "gap", "foundation", "score", "weak", "goal", "exam"],
				"criterion": "Need Generation",
			},
			{
				"key": "pitch",
				"customer": "So what exactly do you people teach?",
				"hint": "Pitch Infinity Learn Foundation / Test Prep and the counsellor demo.",
				"keywords": ["infinity", "foundation", "test prep", "demo", "live", "mentor", "program"],
				"criterion": "Session Pitching",
			},
			{
				"key": "close",
				"customer": "I will think and call you back.",
				"hint": "Close with a specific demo slot instead of leaving it open.",
				"keywords": ["demo", "slot", "tomorrow", "book", "confirm", "calendar", "time"],
				"criterion": "Closing",
			},
		],
	},
	{
		"scenario_key": "cbse-foundation-objection",
		"title": "CBSE Foundation objection",
		"source_crt": "CRT 2",
		"customer_name": "Mr. Reddy",
		"customer_role": "Parent — Class 8 CBSE",
		"objective": "Handle the “school is enough” objection and position CBSE Foundation.",
		"context": (
			"Mr. Reddy believes school tuition is sufficient for Class 8. CRT product sessions "
			"cover why Foundation builds concepts before Test Prep."
		),
		"instructions": (
			"Do not argue. Discover the child’s current marks, explain Foundation vs school "
			"tuition, and invite him to a short demo."
		),
		"sort_order": 2,
		"beats": [
			{
				"key": "open",
				"customer": "Yes, tell me. I already have tuition near our house.",
				"hint": "Introduce yourself and acknowledge the existing tuition.",
				"keywords": ["infinity", "myself", "tuition", "understand", "calling"],
				"criterion": "Introduction",
			},
			{
				"key": "rapport",
				"customer": "School plus tuition is already a lot for him.",
				"hint": "Empathise and ask about current performance.",
				"keywords": ["understand", "marks", "math", "science", "load", "child"],
				"criterion": "Rapport Building",
			},
			{
				"key": "need",
				"customer": "He scores around 70. Why do we need one more class?",
				"hint": "Show the gap between 70 and a strong Foundation for later JEE/NEET.",
				"keywords": ["70", "concept", "gap", "foundation", "later", "jee", "neet", "board"],
				"criterion": "Need Generation",
			},
			{
				"key": "pitch",
				"customer": "Is this the same as school syllabus or some entrance thing?",
				"hint": "Position CBSE Foundation — school syllabus + stronger concepts.",
				"keywords": ["cbse", "foundation", "school", "concept", "not test prep", "class 8"],
				"criterion": "Session Pitching",
			},
			{
				"key": "close",
				"customer": "Send me a brochure. I will decide with my wife.",
				"hint": "Book a demo so both parents can see a live class, not only a brochure.",
				"keywords": ["demo", "live", "wife", "tomorrow", "slot", "see"],
				"criterion": "Closing",
			},
		],
	},
	{
		"scenario_key": "math-champ-need",
		"title": "Math Champ need generation",
		"source_crt": "CRT 3",
		"customer_name": "Mrs. Iyer",
		"customer_role": "Parent — Class 6",
		"objective": "Discover math anxiety and recommend Math Champ, not a generic program.",
		"context": (
			"CRT Day 3 covers Math Champ. The child is scared of math and avoids homework. "
			"Do not pitch Test Prep."
		),
		"instructions": "Ask about current math marks, homework behaviour, and confidence. Then recommend Math Champ.",
		"sort_order": 3,
		"beats": [
			{
				"key": "open",
				"customer": "Hello, I filled a form yesterday. What program is this?",
				"hint": "Introduce Infinity Learn and confirm you are following up on her form.",
				"keywords": ["infinity", "form", "myself", "counsellor", "follow"],
				"criterion": "Introduction",
			},
			{
				"key": "rapport",
				"customer": "My son gets very tense before math tests.",
				"hint": "Acknowledge the fear and ask a warm follow-up.",
				"keywords": ["understand", "tense", "fear", "homework", "son", "sorry"],
				"criterion": "Rapport Building",
			},
			{
				"key": "need",
				"customer": "He can do sums if I sit with him, otherwise he leaves them.",
				"hint": "Need-gen: dependence, confidence, conceptual gaps.",
				"keywords": ["sit", "concept", "confidence", "practice", "gap", "independent"],
				"criterion": "Need Generation",
			},
			{
				"key": "pitch",
				"customer": "Is this IIT coaching? He is only in 6th.",
				"hint": "Pitch Math Champ — not IIT coaching. Fun + concepts for Class 6.",
				"keywords": ["math champ", "not iit", "class 6", "concept", "fun", "foundation"],
				"criterion": "Session Pitching",
			},
			{
				"key": "close",
				"customer": "We already have Byju’s pending.",
				"hint": "Differentiate and close a trial/demo without attacking the other brand.",
				"keywords": ["demo", "live", "try", "see", "slot", "difference"],
				"criterion": "Closing",
			},
		],
	},
	{
		"scenario_key": "testprep-vs-foundation",
		"title": "Test Prep vs Foundation",
		"source_crt": "CRT 3",
		"customer_name": "Mr. Khan",
		"customer_role": "Parent — Class 11 JEE",
		"objective": "Recommend the correct program. Do not sell Foundation to a Class 11 JEE parent.",
		"context": "CRT product sessions distinguish Foundation (younger classes) from Test Prep (JEE/NEET).",
		"instructions": "Ask the target exam and current class, then pitch JEE Test Prep and a counsellor demo.",
		"sort_order": 4,
		"beats": [
			{
				"key": "open",
				"customer": "Someone from Infinity Learn messaged me about Foundation.",
				"hint": "Introduce yourself and clarify you will recommend based on his child’s class.",
				"keywords": ["infinity", "myself", "class", "recommend", "understand"],
				"criterion": "Introduction",
			},
			{
				"key": "rapport",
				"customer": "He just started 11th. Coaching has already begun in Hyderabad.",
				"hint": "Acknowledge existing coaching and ask which exam.",
				"keywords": ["11", "jee", "coaching", "hyderabad", "which exam"],
				"criterion": "Rapport Building",
			},
			{
				"key": "need",
				"customer": "He wants JEE but physics is weak and the local centre is too packed.",
				"hint": "Need: weak physics, batch size, doubt support.",
				"keywords": ["physics", "doubt", "batch", "weak", "jee", "mentor"],
				"criterion": "Need Generation",
			},
			{
				"key": "pitch",
				"customer": "So you will put him in Foundation with 8th graders?",
				"hint": "Correct the mix-up. Pitch JEE Test Prep, not Foundation.",
				"keywords": ["test prep", "jee", "not foundation", "class 11", "live"],
				"criterion": "Session Pitching",
			},
			{
				"key": "close",
				"customer": "Give me a discount first, then we will see.",
				"hint": "Do not lead with discount. Close a demo so he can judge the teaching.",
				"keywords": ["demo", "first", "teaching", "slot", "see the class"],
				"criterion": "Closing",
			},
		],
	},
	{
		"scenario_key": "lsq-process-call",
		"title": "LSQ process adherence",
		"source_crt": "CRT 4",
		"customer_name": "Mrs. Das",
		"customer_role": "Website lead — Class 9",
		"objective": "Run the CRT Day 4 LSQ process: capture need, update disposition, book next action.",
		"context": (
			"This lead is already in LSQ. You must follow process: confirm details, ask mandatory "
			"discovery, and close with a logged next step — not a casual chat."
		),
		"instructions": "Stay on process. Mention LSQ fields only in natural language (class, board, next action).",
		"sort_order": 5,
		"beats": [
			{
				"key": "open",
				"customer": "You people keep calling. I already spoke to someone yesterday.",
				"hint": "Introduce yourself, own the follow-up, and confirm her details.",
				"keywords": ["infinity", "follow", "yesterday", "myself", "confirm"],
				"criterion": "Introduction",
			},
			{
				"key": "rapport",
				"customer": "I don’t want to repeat everything again.",
				"hint": "Apologise briefly and confirm class/board instead of restarting.",
				"keywords": ["sorry", "class 9", "board", "confirm", "quick"],
				"criterion": "Rapport Building",
			},
			{
				"key": "need",
				"customer": "We want something for 9th CBSE, mainly science.",
				"hint": "Capture need: class, board, subject, goal.",
				"keywords": ["cbse", "science", "9", "goal", "foundation"],
				"criterion": "Need Generation",
			},
			{
				"key": "pitch",
				"customer": "Okay, send a link on WhatsApp.",
				"hint": "Pitch the right program and a scheduled demo, not only a WhatsApp dump.",
				"keywords": ["demo", "program", "foundation", "live", "counsellor"],
				"criterion": "Session Pitching",
			},
			{
				"key": "close",
				"customer": "I said I am busy now.",
				"hint": "Agree a callback slot and state you will log it as the next action.",
				"keywords": ["callback", "slot", "tomorrow", "log", "next", "time"],
				"criterion": "Closing",
			},
		],
	},
]


def seed_ojt_scenarios():
	for spec in SCENARIOS:
		payload = {
			"doctype": "Sales OJT Scenario",
			"scenario_key": spec["scenario_key"],
			"title": spec["title"],
			"enabled": 1,
			"sort_order": spec["sort_order"],
			"source_crt": spec["source_crt"],
			"customer_name": spec["customer_name"],
			"customer_role": spec["customer_role"],
			"objective": spec["objective"],
			"context": spec["context"],
			"instructions": spec["instructions"],
			"script_json": json.dumps({"beats": spec["beats"]}),
		}
		if frappe.db.exists("Sales OJT Scenario", spec["scenario_key"]):
			doc = frappe.get_doc("Sales OJT Scenario", spec["scenario_key"])
			doc.update({k: v for k, v in payload.items() if k != "doctype"})
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(payload).insert(ignore_permissions=True)


def get_beats(scenario) -> list[dict]:
	raw = scenario.script_json if hasattr(scenario, "script_json") else scenario.get("script_json")
	if not raw:
		fallback = next((s for s in SCENARIOS if s["scenario_key"] == scenario.get("scenario_key")), None)
		return list(fallback["beats"]) if fallback else []
	data = json.loads(raw) if isinstance(raw, str) else raw
	return data.get("beats") or []


def opening_customer_line(scenario) -> str:
	beats = get_beats(scenario)
	return beats[0]["customer"] if beats else "Hello?"


def score_message(text: str, beat: dict) -> tuple[float, bool]:
	blob = (text or "").lower()
	hits = 0
	for word in beat.get("keywords") or []:
		if word.lower() in blob:
			hits += 1
	needed = max(1, min(2, len(beat.get("keywords") or [])))
	passed = hits >= needed or (hits >= 1 and len(blob.split()) >= 12)
	score = min(100.0, (hits / max(1, len(beat.get("keywords") or []))) * 100)
	if passed and score < 60:
		score = 60
	return score, passed


def advance_after_learner(attempt, learner_text: str) -> dict:
	scenario = frappe.get_doc("Sales OJT Scenario", attempt.scenario)
	beats = get_beats(scenario)
	idx = cint(attempt.beat_index)
	now = now_datetime()
	reply = None
	finished = False
	hint = None
	current_key = beats[idx]["key"] if beats and idx < len(beats) else ""

	if idx >= len(beats):
		finished = True
	else:
		beat = beats[idx]
		_score, passed = score_message(learner_text, beat)
		if passed:
			idx += 1
			attempt.beat_index = idx
			if idx < len(beats):
				reply = beats[idx]["customer"]
				hint = beats[idx].get("hint")
			else:
				finished = True
				reply = (
					"Alright… I will wait for the demo confirmation. Thank you for the call."
				)
		else:
			hint = beat.get("hint")
			reply = (
				f"{scenario.customer_name.split()[0]} still sounds unsure. "
				f"{hint or 'Try covering the point this beat needs.'}"
			)

	attempt.append(
		"messages",
		{"role": "learner", "content": learner_text, "beat_key": current_key, "created_at": now},
	)
	if reply:
		next_key = beats[min(idx, len(beats) - 1)]["key"] if beats else ""
		attempt.append(
			"messages",
			{"role": "customer", "content": reply, "beat_key": next_key, "created_at": now},
		)
	return {"reply": reply, "finished": finished, "hint": hint, "beat_index": idx}


def evaluate_attempt(attempt) -> dict:
	scenario = frappe.get_doc("Sales OJT Scenario", attempt.scenario)
	beats = get_beats(scenario)
	learner_msgs = [m for m in attempt.messages if m.role == "learner"]
	by_key = {}
	for msg in learner_msgs:
		by_key.setdefault(msg.beat_key or "", []).append(msg.content or "")

	scores = []
	strengths = []
	improvements = []
	for beat in beats:
		joined = " ".join(by_key.get(beat["key"], []))
		score, passed = score_message(joined, beat)
		scores.append(
			{
				"criterion": beat["criterion"],
				"score": score,
				"max_score": 100,
				"notes": "Covered in the call." if passed else (beat.get("hint") or "Needs a stronger response."),
			}
		)
		if passed:
			strengths.append(beat["criterion"])
		else:
			improvements.append(beat.get("hint") or beat["criterion"])

	# Collapse duplicate criteria (same rubric used across beats)
	rolled = {}
	for row in scores:
		cur = rolled.setdefault(row["criterion"], {"total": 0.0, "n": 0, "notes": []})
		cur["total"] += row["score"]
		cur["n"] += 1
		if row["notes"]:
			cur["notes"].append(row["notes"])
	final = [
		{
			"criterion": name,
			"score": round(val["total"] / val["n"], 1),
			"max_score": 100,
			"notes": "; ".join(dict.fromkeys(val["notes"])),
		}
		for name, val in rolled.items()
	]
	overall = round(sum(r["score"] for r in final) / max(1, len(final)), 1)
	return {
		"scores": final,
		"overall_score": overall,
		"strengths": ", ".join(dict.fromkeys(strengths)) or "Keep practising the opening and close.",
		"improvements": "; ".join(dict.fromkeys(improvements)) or "Maintain this standard on live calls.",
	}
