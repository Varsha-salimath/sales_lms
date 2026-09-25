# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Sales CRT learner reports: the combined (batch) report and the individual report card.

Source of truth is `Sales OJT Certification Metric` (synced from the OJT sheet). Scores are
normalised to a percentage with the scales below so different metrics can share one colour scale
(the same Excellent / Good / Average / Needs Improvement bands as the student PTM report).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from lms.lms import access
from lms.lms.library import get_batch_code
from lms.lms.ojt_certification import DOCTYPE

# OJT sheet rows are Sales CRT trainees; until they have LMS accounts they belong to this team.
OJT_DEPARTMENT = "Retail Sales"


def _ensure_report_access():
	"""Training Managers and above (and trainers) may open learner reports.

	A Training Manager can be an ordinary user with people reporting to them, so the tier check
	alone turned them away from the reports the sidebar offers them. `_scoped` then limits the rows
	to their own people.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("You do not have access to learner reports."), frappe.PermissionError)
	if access.get_tier() < access.INSTRUCTOR and not access.is_training_manager():
		frappe.throw(_("You do not have access to learner reports."), frappe.PermissionError)


def _scoped(rows):
	"""Rows the current user may see: their department, their people, or trainees they manage."""
	user = frappe.session.user
	if access.can_view_department(OJT_DEPARTMENT, user):
		return rows
	me = user.lower()
	me_email = (frappe.db.get_value("User", user, "email") or user or "").strip().lower()
	tm_tree = access.training_manager_tree(user)
	# Training Manager without instructor/admin tier: only TM reporting-line learners.
	if access.get_tier(user) < access.INSTRUCTOR and tm_tree:
		tm_emails = set()
		for member in tm_tree:
			email = (frappe.db.get_value("User", member, "email") or member or "").strip().lower()
			tm_emails.add(email)
			tm_emails.add(member.lower())
		return [
			r
			for r in rows
			if (r.email or "").lower() in tm_emails
			or (r.training_manager or "").lower() in {me, me_email}
		]
	visible = access.get_visible_members(user)
	visible = {v.lower() for v in visible} if visible is not access.EVERYONE else None
	tm_emails = set()
	if tm_tree:
		for member in tm_tree:
			email = (frappe.db.get_value("User", member, "email") or member or "").strip().lower()
			tm_emails.add(email)
			tm_emails.add(member.lower())
	return [
		r
		for r in rows
		if visible is None
		or (r.email or "").lower() in visible
		or (r.email or "").lower() in tm_emails
		or (r.training_manager or "").lower() in {me, me_email}
		or (r.training_manager or "").lower() in visible
	]

# Max value for each metric. Change here if a scale changes (e.g. a longer CRT).
SCALES = {
	"attendance_days": 15,  # 15-day CRT
	"ai_mock_score": 20,
	"audit_score": 20,
	"target_exam": 20,
	"cbse": 20,
	"test_prep": 20,
	"lsq": 20,
	"math_champ": 20,
}

METRICS = [
	# key, label, group
	("attendance_days", "Attendance", "intent"),
	("ai_mock_score", "AI Mock", "intent"),
	("audit_score", "Audit", "intent"),
	("target_exam", "Target Exam", "tests"),
	("cbse", "CBSE", "tests"),
	("test_prep", "Test Prep", "tests"),
	("lsq", "LSQ", "tests"),
	("math_champ", "Math Champ", "tests"),
]
CALLING = ("dc", "cc", "talk_time", "booked", "catered")

# Readiness = average of these components (each as % of its scale).
READINESS_PARTS = ("attendance_days", "ai_mock_score", "audit_score", "product_avg")

BANDS = [  # (min %, key, label)
	(90, "excellent", "Excellent"),
	(80, "good", "Good"),
	(60, "average", "Average"),
	(0, "needs_improvement", "Needs Improvement"),
]

FIELDS = [
	"name",
	"learner",
	"employee_name",
	"email",
	"location",
	"training_manager",
	"batch_start",
	"attendance_days",
	"ai_mock_score",
	"audit_score",
	"product_avg",
	"stage",
	"dc",
	"cc",
	"talk_time",
	"booked",
	"catered",
	"target_exam",
	"cbse",
	"test_prep",
	"lsq",
	"math_champ",
	"modified",
]


# ---------------------------------------------------------------------------
# Scoring helpers (pure)
# ---------------------------------------------------------------------------


def pct(key, value):
	if value is None or value == "":
		return None
	scale = SCALES.get(key, 20 if key == "product_avg" else None)
	if not scale:
		return None
	return round(min(flt(value) / scale, 1) * 100, 1)


def band(percent):
	if percent is None:
		return None
	for minimum, key, _label in BANDS:
		if percent >= minimum:
			return key
	return BANDS[-1][1]


def readiness(row):
	parts = [pct(key, row.get(key)) for key in READINESS_PARTS]
	parts = [p for p in parts if p is not None]
	if not parts:
		return None
	return round(sum(parts) / len(parts), 1)


def talk_seconds(value):
	"""'15:17:37' -> seconds. Talk time is stored as text from the sheet."""
	if not value:
		return None
	try:
		parts = [int(p) for p in str(value).strip().split(":")]
	except ValueError:
		return None
	while len(parts) < 3:
		parts.insert(0, 0)
	h, m, s = parts[-3:]
	return h * 3600 + m * 60 + s


def ratio(numerator, denominator):
	if not denominator or numerator is None:
		return None
	return round(flt(numerator) / flt(denominator) * 100, 1)


def enrich(row):
	row = frappe._dict(row)
	row.readiness = readiness(row)
	row.readiness_band = band(row.readiness)
	row.scores = {
		key: {"value": row.get(key), "pct": pct(key, row.get(key)), "band": band(pct(key, row.get(key)))}
		for key, _label, _group in METRICS
	}
	row.connect_rate = ratio(row.cc, row.dc)
	row.booking_rate = ratio(row.booked, row.cc)
	row.show_rate = ratio(row.catered, row.booked)
	row.talk_seconds = talk_seconds(row.talk_time)
	return row


def cohort_stats(rows):
	"""{metric: {avg, min, max, count}} over rows that have a value."""
	keys = [k for k, _l, _g in METRICS] + [
		"product_avg",
		"readiness",
		"dc",
		"cc",
		"booked",
		"catered",
		"talk_seconds",
		"connect_rate",
		"booking_rate",
		"show_rate",
	]
	stats = {}
	for key in keys:
		values = [flt(r.get(key)) for r in rows if r.get(key) not in (None, "")]
		if not values:
			stats[key] = {"avg": None, "min": None, "max": None, "count": 0}
			continue
		stats[key] = {
			"avg": round(sum(values) / len(values), 1),
			"min": min(values),
			"max": max(values),
			"count": len(values),
		}
	return stats


def label_of(key):
	return next((label for k, label, _g in METRICS if k == key), key)


def learner_insights(row, stats):
	"""Plain-language strengths and gaps versus the batch."""
	strengths, gaps = [], []
	for key, label, _group in METRICS:
		value, avg = row.get(key), stats.get(key, {}).get("avg")
		if value in (None, "") or avg is None:
			continue
		diff = flt(value) - avg
		p = pct(key, value)
		if p is not None and p >= 90:
			strengths.append(_("{0} is excellent ({1}%).").format(label, p))
		elif diff >= 2:
			strengths.append(_("{0} is {1} above the batch average.").format(label, round(diff, 1)))
		if p is not None and p < 60:
			gaps.append(_("{0} needs work ({1}% of max).").format(label, p))
		elif diff <= -2:
			gaps.append(_("{0} is {1} below the batch average.").format(label, round(-diff, 1)))
	if row.booking_rate is not None and stats["booking_rate"]["avg"] is not None:
		if row.booking_rate < stats["booking_rate"]["avg"] - 2:
			gaps.append(
				_("Books {0}% of connected calls vs {1}% batch average.").format(
					row.booking_rate, stats["booking_rate"]["avg"]
				)
			)
		elif row.booking_rate > stats["booking_rate"]["avg"] + 2:
			strengths.append(
				_("Converts {0}% of connected calls to bookings vs {1}% average.").format(
					row.booking_rate, stats["booking_rate"]["avg"]
				)
			)
	return {"strengths": strengths[:4], "gaps": gaps[:4]}


def batch_insights(rows, stats):
	lines = []
	if not rows:
		return lines
	ready = [r for r in rows if r.readiness_band in ("excellent", "good")]
	lines.append(
		_("{0} of {1} learners are at Good or better readiness.").format(len(ready), len(rows))
	)
	test_avgs = sorted(
		((label, stats[key]["avg"]) for key, label, group in METRICS if group == "tests" and stats[key]["avg"] is not None),
		key=lambda item: item[1],
	)
	if test_avgs:
		lines.append(
			_("Strongest test: {0} (avg {1}/20). Weakest: {2} (avg {3}/20).").format(
				test_avgs[-1][0], test_avgs[-1][1], test_avgs[0][0], test_avgs[0][1]
			)
		)
	if stats["booking_rate"]["avg"] is not None:
		lines.append(
			_("Batch books {0}% of connected calls; {1}% of bookings are catered.").format(
				stats["booking_rate"]["avg"], stats["show_rate"]["avg"] or 0
			)
		)
	needs = [r.employee_name for r in rows if r.readiness_band == "needs_improvement"]
	if needs:
		lines.append(
			_("Needs attention: {0}.").format(", ".join(needs[:5]) + (" …" if len(needs) > 5 else ""))
		)
	return lines


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _batch_code_index():
	"""Map batch code (from LMS Batch title) -> list of LMS Batch names."""
	mapping = {}
	for batch in frappe.get_all("LMS Batch", fields=["name", "title"]):
		code = get_batch_code(batch.title)
		if code:
			mapping.setdefault(code, []).append(batch.name)
	return mapping


def _emails_for_batch_code(batch_code: str) -> set[str]:
	batch_names = _batch_code_index().get(batch_code, [])
	if not batch_names:
		return set()
	members = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"batch": ["in", batch_names]},
		pluck="member",
	)
	if not members:
		return set()
	emails = set()
	for user in frappe.get_all(
		"User",
		filters={"name": ["in", members], "enabled": 1},
		fields=["name", "email"],
	):
		if user.email:
			emails.add(user.email.lower())
		emails.add(user.name.lower())
	return emails


def _learner_emails_for_training_manager(training_manager: str) -> set[str]:
	"""OJT sheet TM email plus learners under this user as Training Manager."""
	emails = {
		(row.email or "").lower()
		for row in frappe.get_all(
			DOCTYPE,
			filters={"training_manager": training_manager},
			fields=["email"],
		)
		if row.email
	}
	tm_user = frappe.db.get_value("User", {"email": training_manager}, "name")
	if not tm_user and frappe.db.exists("User", training_manager):
		tm_user = training_manager
	if tm_user:
		for member in access.training_manager_tree(tm_user):
			user = frappe.db.get_value("User", member, ["email", "name"], as_dict=True)
			if not user:
				continue
			if user.email:
				emails.add(user.email.lower())
			emails.add(user.name.lower())
	return emails


def _ojt_batch_start_codes(training_manager: str | None) -> list[str]:
	"""Distinct OJT sheet batch_start values (CRT rows often have no LMS Batch enrollment)."""
	filters = {}
	if training_manager and training_manager != "__all__":
		filters["training_manager"] = training_manager
	starts = frappe.get_all(
		DOCTYPE,
		filters=filters,
		fields=["batch_start"],
		distinct=True,
		order_by="batch_start desc",
	)
	return sorted({str(row.batch_start) for row in starts if row.batch_start})


def _batch_codes_for_training_manager(training_manager: str | None) -> list[str]:
	code_map = _batch_code_index()
	ojt_codes = set(_ojt_batch_start_codes(training_manager))
	if not training_manager or training_manager == "__all__":
		return sorted(set(code_map.keys()) | ojt_codes)
	learner_emails = _learner_emails_for_training_manager(training_manager)
	lms_codes = set()
	if learner_emails:
		for code, batch_names in code_map.items():
			members = frappe.get_all(
				"LMS Batch Enrollment",
				filters={"batch": ["in", batch_names]},
				pluck="member",
			)
			if not members:
				continue
			for user in frappe.get_all(
				"User",
				filters={"name": ["in", members]},
				fields=["email", "name"],
			):
				email = (user.email or user.name or "").lower()
				if email in learner_emails:
					lms_codes.add(code)
					break
	return sorted(lms_codes | ojt_codes)


def _rows(
	batch_start=None,
	batch_code=None,
	location=None,
	training_manager=None,
	search=None,
):
	filters = {}
	if batch_start and batch_start != "__all__":
		filters["batch_start"] = getdate(batch_start)
	if location and location != "__all__":
		filters["location"] = location
	if training_manager and training_manager != "__all__":
		filters["training_manager"] = training_manager
	or_filters = None
	if search:
		term = f"%{search.strip()}%"
		or_filters = {"employee_name": ["like", term], "email": ["like", term]}
	sheet_rows = frappe.get_all(
		DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		fields=FIELDS,
		order_by="employee_name asc",
		limit_page_length=0,
	)
	rows = [enrich(r) for r in _with_test_scores(sheet_rows)]
	rows += _lms_rows({(r.email or "").lower() for r in rows}, batch_start, location, training_manager, search)
	rows.sort(key=lambda r: (r.employee_name or r.email or "").lower())
	if batch_code and batch_code != "__all__":
		allowed = _emails_for_batch_code(batch_code)
		if allowed:
			rows = [r for r in rows if (r.email or "").lower() in allowed]
		else:
			try:
				target = getdate(batch_code)
			except Exception:
				target = None
			if target:
				rows = [r for r in rows if r.batch_start and getdate(r.batch_start) == target]
			else:
				rows = []
	return rows


# ---------------------------------------------------------------------------
# Test scores from the LMS
# ---------------------------------------------------------------------------

# The CRT quizzes are the product tests. Each is out of 20, the same scale as the sheet columns.
QUIZ_TO_TEST = {
	"crt-1-target-exam-quiz": "target_exam",
	"crt-2-cbse-foundation-quiz": "cbse",
	"crt-2-math-champ-quiz": "math_champ",
	"crt-3-test-prep-quiz": "test_prep",
	"crt-4-lsq-quiz": "lsq",
}
TEST_SCALE = 20


def _quiz_scores(users) -> dict:
	"""{user: {test_field: best score out of 20}} from LMS quiz attempts."""
	users = sorted({u for u in users if u})
	if not users:
		return {}
	out: dict = {}
	for sub in frappe.get_all(
		"LMS Quiz Submission",
		{"member": ["in", users], "quiz": ["in", list(QUIZ_TO_TEST)]},
		["member", "quiz", "percentage"],
	):
		field = QUIZ_TO_TEST[sub.quiz]
		score = round(flt(sub.percentage) / 100 * TEST_SCALE, 1)
		mine = out.setdefault(sub.member.lower(), {})
		mine[field] = max(score, mine.get(field) or 0)
	return out


def _with_test_scores(rows):
	"""Tests come from the LMS: a learner's best quiz attempt fills the matching column.

	Attendance, calls and demos stay as the OJT sheet has them — those are recorded outside the LMS.
	A sheet value is only used for a test the learner hasn't taken in the LMS.
	"""
	from lms.lms.ojt_certification import derive_product_avg, derive_stage

	scores = _quiz_scores([_learner_user(r) for r in rows])
	for row in rows:
		mine = scores.get(_learner_user(row)) or {}
		sources = {}
		for field in QUIZ_TO_TEST.values():
			if field in mine:
				row[field] = mine[field]
				sources[field] = "lms"
			elif row.get(field) not in (None, ""):
				sources[field] = "sheet"
		if mine:
			row["product_avg"] = derive_product_avg(row)
			row["stage"] = derive_stage(row)
		row["test_sources"] = sources
	return rows


# ---------------------------------------------------------------------------
# Learners who are in the LMS but not (yet) in the OJT sheet
# ---------------------------------------------------------------------------

LMS_ROW_PREFIX = "lms:"
STAFF_ROLES = ("Admin", "Manager", "Instructor")


def _active_learners() -> set[str]:
	"""Everyone actually learning: in a batch, or with CRT progress or a viva, and not staff.

	The report used to list only people in the OJT Google Sheet, so a learner added through the LMS
	(a batch upload, a CRT enrollment) never appeared however much they did.
	"""
	in_batch = set(frappe.get_all("LMS Batch Enrollment", pluck="member"))
	crt = set(frappe.get_all("LMS Course Progress", {"course": "sales-crt"}, pluck="member", distinct=True))
	if frappe.db.table_exists("Sales Viva Attempt"):
		crt |= set(frappe.get_all("Sales Viva Attempt", pluck="member", distinct=True))
	staff = set(frappe.get_all("LMS Member", {"access_role": ["in", STAFF_ROLES]}, pluck="name"))
	# Admins and trainers testing the CRT or a viva aren't learners (System Managers have no
	# LMS Member row, so the tier catches them too).
	staff |= {u for u in crt if access.get_tier(u) >= access.INSTRUCTOR}
	# Someone in a batch is a learner there, even a manager on a managers' course.
	return {u for u in in_batch | (crt - staff) if u and u not in ("Administrator", "Guest")}


def _lms_row(user: str) -> frappe._dict | None:
	info = frappe.db.get_value("User", user, ["name", "full_name", "email", "modified"], as_dict=True)
	if not info:
		return None
	email = (info.email or info.name).lower()
	manager = frappe.db.get_value(
		"LMS Reporting Line",
		{"member": user, "line_type": "Training Manager", "status": "Active"},
		"manager",
	)
	latest_batch = frappe.get_all(
		"LMS Batch Enrollment", {"member": user}, ["batch"], order_by="creation desc", limit=1
	)
	batch_start = (
		frappe.db.get_value("LMS Batch", latest_batch[0].batch, "start_date") if latest_batch else None
	)
	activity = frappe.db.sql(
		"select max(modified) from `tabLMS Course Progress` where member=%s", user
	)[0][0]
	row = {field: None for field in FIELDS}
	row.update(
		{
			"name": f"{LMS_ROW_PREFIX}{user}",
			"learner": user,
			"employee_name": info.full_name or email,
			"email": email,
			"training_manager": (frappe.db.get_value("User", manager, "email") or manager or "").lower() or None,
			"batch_start": batch_start,
			"modified": activity or info.modified,
		}
	)
	row = enrich(_with_test_scores([row])[0])
	row.source = "lms"  # no OJT sheet row yet: attendance and demos are empty, not zero
	return row


def _lms_rows(known_emails: set[str], batch_start=None, location=None, training_manager=None, search=None):
	if location and location != "__all__":
		return []  # location comes from the OJT sheet; LMS-only learners don't have one yet
	target_start = getdate(batch_start) if batch_start and batch_start != "__all__" else None
	term = (search or "").strip().lower()
	out = []
	for user in sorted(_active_learners()):
		email = (frappe.db.get_value("User", user, "email") or user).lower()
		if email in known_emails or user.lower() in known_emails:
			continue
		row = _lms_row(user)
		if not row:
			continue
		if target_start and (not row.batch_start or getdate(row.batch_start) != target_start):
			continue
		if training_manager and training_manager != "__all__" and row.training_manager != training_manager.lower():
			continue
		if term and term not in (row.employee_name or "").lower() and term not in email:
			continue
		out.append(row)
	return out


def _options(field):
	return [
		v
		for v in frappe.get_all(DOCTYPE, fields=[field], distinct=True, order_by=f"{field} desc", pluck=field)
		if v
	]


def _training_manager_filter_options() -> list[str]:
	emails = set(_options("training_manager"))
	for row in frappe.get_all(
		"LMS Reporting Line",
		filters={"line_type": "Training Manager", "status": "Active"},
		fields=["manager"],
		distinct=True,
	):
		manager = row.manager
		if not manager:
			continue
		email = (frappe.db.get_value("User", manager, "email") or manager or "").strip().lower()
		if email:
			emails.add(email)
	user = frappe.session.user
	if access.get_tier() < access.INSTRUCTOR and access.training_manager_tree(user):
		me = (frappe.db.get_value("User", user, "email") or user or "").strip().lower()
		return sorted({me} & emails or {me})
	return sorted(emails)


def _learner_user(row) -> str:
	return (row.get("learner") or row.get("email") or "").strip().lower()


def viva_summary(users, course: str = "sales-crt") -> dict:
	"""Voice viva results per user: best score per day, pass state, attempts, watch-outs."""
	users = sorted({u for u in users if u})
	if not users or not frappe.db.table_exists("Sales Viva Attempt"):
		return {}
	from lms.lms.sales_viva import day_title

	titles = {}
	out = {}
	for a in frappe.get_all(
		"Sales Viva Attempt",
		{"member": ["in", users], "course": course, "status": ["in", ["Passed", "Not Passed"]]},
		["name", "member", "crt_number", "status", "overall_score", "knowledge_score", "fluency_score", "watch_outs", "started_at"],
		order_by="started_at asc",
	):
		user = out.setdefault(a.member.lower(), {"days": {}})
		day = user["days"].setdefault(
			a.crt_number,
			{"day": a.crt_number, "attempts": 0, "best": None, "passed": False, "best_attempt": None, "flags": 0},
		)
		day["attempts"] += 1
		day["passed"] = day["passed"] or a.status == "Passed"
		if day["best"] is None or flt(a.overall_score) > day["best"]:
			day.update(
				best=flt(a.overall_score),
				knowledge=flt(a.knowledge_score),
				fluency=flt(a.fluency_score),
				best_attempt=a.name,
				flags=len([f for f in (a.watch_outs or "").split("\n") if f]),
			)
	for user in out.values():
		days = sorted(user["days"].values(), key=lambda d: d["day"])
		for d in days:
			if d["day"] not in titles:
				titles[d["day"]] = day_title(course, d["day"])
			d["title"] = titles[d["day"]]
		user["days"] = days
		user["avg"] = round(sum(d["best"] for d in days) / len(days), 1) if days else None
		user["passed_days"] = sum(1 for d in days if d["passed"])
	return out


@frappe.whitelist()
def get_combined_report(
	batch_start: str | None = None,
	batch_code: str | None = None,
	location: str | None = None,
	training_manager: str | None = None,
	search: str | None = None,
):
	_ensure_report_access()
	rows = _scoped(_rows(batch_start, batch_code, location, training_manager, search))
	vivas = viva_summary([_learner_user(r) for r in rows])
	for r in rows:
		v = vivas.get(_learner_user(r)) or {}
		r.viva_avg = v.get("avg")
		r.viva_passed_days = v.get("passed_days", 0)
	stats = cohort_stats(rows)
	bands = {key: 0 for _m, key, _l in BANDS}
	for r in rows:
		if r.readiness_band:
			bands[r.readiness_band] += 1
	last_updated = max((r.modified for r in rows if r.modified), default=None)
	tm_options = _training_manager_filter_options()
	default_tm = None
	if access.get_tier() < access.INSTRUCTOR and access.training_manager_tree(frappe.session.user):
		me = (frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user or "").strip().lower()
		if me in tm_options:
			default_tm = me
	return {
		"rows": rows,
		"stats": stats,
		"bands": [
			{"key": key, "label": _(label), "min": minimum, "count": bands[key]} for minimum, key, label in BANDS
		],
		"insights": batch_insights(rows, stats),
		"metrics": [{"key": k, "label": _(l), "group": g, "max": SCALES[k]} for k, l, g in METRICS],
		"options": {
			"batch_code": _batch_codes_for_training_manager(training_manager),
			"location": sorted(_options("location")),
			"training_manager": tm_options,
		},
		"default_training_manager": default_tm,
		"last_updated": last_updated,
	}


@frappe.whitelist()
def get_learner_report(name: str):
	_ensure_report_access()
	if name and name.startswith(LMS_ROW_PREFIX):
		row = _lms_row(name[len(LMS_ROW_PREFIX):])
		if not row:
			frappe.throw(_("Learner report not found"))
	elif not name or not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("Learner report not found"))
	else:
		row = enrich(_with_test_scores([frappe.db.get_value(DOCTYPE, name, FIELDS, as_dict=True)])[0])
	if not _scoped([row]):
		frappe.throw(_("You do not have access to this learner's report."), frappe.PermissionError)
	cohort = _rows(batch_start=row.batch_start) if row.batch_start else [row]
	stats = cohort_stats(cohort)

	ranked = sorted((r for r in cohort if r.readiness is not None), key=lambda r: r.readiness, reverse=True)
	rank = next((i + 1 for i, r in enumerate(ranked) if r.name == row.name), None)

	profile = {}
	if row.learner:
		profile = frappe.db.get_value(
			"User", row.learner, ["full_name", "user_image", "mobile_no", "username"], as_dict=True
		) or {}

	viva = viva_summary([_learner_user(row)]).get(_learner_user(row)) or {"days": [], "avg": None, "passed_days": 0}
	return {
		"learner": row,
		"profile": profile,
		"viva": viva,
		"batch": {"batch_start": row.batch_start, "size": len(cohort), "rank": rank, "ranked": len(ranked)},
		"stats": stats,
		"insights": learner_insights(row, stats),
		"metrics": [{"key": k, "label": _(l), "group": g, "max": SCALES[k]} for k, l, g in METRICS],
		"bands": [{"key": key, "label": _(label), "min": minimum} for minimum, key, label in BANDS],
	}
