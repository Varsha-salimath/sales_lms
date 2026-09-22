"""Time tracking APIs — heartbeat ingestion and analytics summaries."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, today

MODULES = ("Courses", "Quiz", "Assignment", "Library", "Programming", "Other")
VALID_MODULES = set(MODULES)

SUMMARY_DAYS = 14
HEATMAP_DAYS = 90
HEARTBEAT_MINUTES = 1
HEARTBEAT_RATE_LIMIT_SECONDS = 25
RAW_HEARTBEAT_RETENTION_DAYS = 30

DISPLAY_GROUPS = {
	"Courses": "Courses",
	"Quiz": "Quizzes",
	"Assignment": "Library / other",
	"Library": "Library / other",
	"Programming": "Library / other",
	"Other": "Library / other",
}


def _ensure_analytics_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator"}):
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)


def _ensure_user_time_access(user_id: str):
	"""Allow users to view their own time data; instructors/admins can view anyone;
	Training Managers can view learners in their reporting tree."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	if user_id == frappe.session.user:
		return
	try:
		_ensure_analytics_access()
		return
	except frappe.PermissionError:
		from lms.lms import access

		if user_id and user_id in access.training_manager_tree(frappe.session.user):
			return
		raise


def _get_user_role(user: str) -> str:
	roles = set(frappe.get_roles(user))
	if roles.intersection({"Administrator", "Moderator"}):
		return "Admin"
	if roles.intersection({"Course Creator", "Batch Evaluator", "Instructor"}):
		return "Teacher"
	return "Student"


def _format_duration(minutes: int) -> str:
	minutes = cint(minutes)
	if minutes <= 0:
		return "0m"
	hours = minutes // 60
	mins = minutes % 60
	if hours and mins:
		return f"{hours}h {mins}m"
	if hours:
		return f"{hours}h"
	return f"{mins}m"


def _heatmap_level(minutes: int) -> int:
	minutes = cint(minutes)
	if minutes <= 0:
		return 0
	if minutes < 30:
		return 1
	if minutes < 90:
		return 2
	if minutes < 180:
		return 3
	return 4


def _percent(part: int, total: int) -> int:
	if not total:
		return 0
	return int(round(flt(part) * 100 / flt(total)))


def _heartbeat_cache_key(user: str) -> str:
	return f"lms:time_tracking:last_heartbeat:{user}"


def _is_rate_limited(user: str, ts) -> bool:
	cache = frappe.cache()
	cache_key = _heartbeat_cache_key(user)
	last_seen = cache.get_value(cache_key)
	current_ts = int(ts.timestamp())

	if last_seen and current_ts - cint(last_seen) < HEARTBEAT_RATE_LIMIT_SECONDS:
		return True

	cache.set_value(cache_key, current_ts, expires_in_sec=HEARTBEAT_RATE_LIMIT_SECONDS)
	return False


@frappe.whitelist()
def send_heartbeat(module: str = "Other"):
	"""Record one active-time heartbeat for the current user."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to track activity."), frappe.PermissionError)

	module = (module or "Other").strip()
	if module not in VALID_MODULES:
		frappe.throw(_("Invalid module: {0}").format(module))

	user = frappe.session.user
	role = _get_user_role(user)
	ts = now_datetime()
	if _is_rate_limited(user, ts):
		return {"ok": True, "skipped": True, "reason": "rate_limited"}

	frappe.get_doc(
		{
			"doctype": "LMS Activity Heartbeat",
			"user": user,
			"role": role,
			"module": module,
			"timestamp": ts,
		}
	).insert(ignore_permissions=True)

	_activity_date = getdate(ts)
	_upsert_today_activity(user, role, module, _activity_date, ts)

	return {"ok": True}


def _upsert_today_activity(user: str, role: str, module: str, activity_date, ts):
	"""Increment today's running total so analytics stay current before nightly rollup."""
	name = frappe.db.get_value(
		"LMS Daily Activity",
		{"user": user, "date": activity_date, "module": module},
	)
	if name:
		frappe.db.set_value(
			"LMS Daily Activity",
			name,
			{
				"minutes_active": cint(frappe.db.get_value("LMS Daily Activity", name, "minutes_active"))
				+ HEARTBEAT_MINUTES,
				"last_heartbeat": ts,
			},
			update_modified=False,
		)
	else:
		frappe.get_doc(
			{
				"doctype": "LMS Daily Activity",
				"user": user,
				"role": role,
				"date": activity_date,
				"module": module,
				"minutes_active": HEARTBEAT_MINUTES,
				"last_heartbeat": ts,
			}
		).insert(ignore_permissions=True)


def _build_user_summary(user_id: str) -> dict:
	summary_start = add_days(today(), -(SUMMARY_DAYS - 1))
	heatmap_start = add_days(today(), -(HEATMAP_DAYS - 1))

	summary_rows = frappe.get_all(
		"LMS Daily Activity",
		filters={"user": user_id, "date": [">=", summary_start]},
		fields=["module", "minutes_active"],
	)

	module_minutes = {m: 0 for m in MODULES}
	for row in summary_rows:
		module_minutes[row.module] = module_minutes.get(row.module, 0) + cint(row.minutes_active)

	total_minutes = sum(module_minutes.values())

	courses_minutes = module_minutes["Courses"]
	quiz_minutes = module_minutes["Quiz"]
	library_other_minutes = (
		module_minutes["Assignment"]
		+ module_minutes["Library"]
		+ module_minutes["Programming"]
		+ module_minutes["Other"]
	)

	summary_cards = [
		{
			"key": "total",
			"label": "Total active",
			"minutes": total_minutes,
			"display": _format_duration(total_minutes),
			"subtext": f"Last {SUMMARY_DAYS} days",
			"percent": None,
		},
		{
			"key": "courses",
			"label": "Courses",
			"minutes": courses_minutes,
			"display": _format_duration(courses_minutes),
			"subtext": f"{_percent(courses_minutes, total_minutes)}% of time",
			"percent": _percent(courses_minutes, total_minutes),
		},
		{
			"key": "quizzes",
			"label": "Quizzes",
			"minutes": quiz_minutes,
			"display": _format_duration(quiz_minutes),
			"subtext": f"{_percent(quiz_minutes, total_minutes)}% of time",
			"percent": _percent(quiz_minutes, total_minutes),
		},
		{
			"key": "library_other",
			"label": "Library / other",
			"minutes": library_other_minutes,
			"display": _format_duration(library_other_minutes),
			"subtext": f"{_percent(library_other_minutes, total_minutes)}% of time",
			"percent": _percent(library_other_minutes, total_minutes),
		},
	]

	heatmap_rows = frappe.db.sql(
		"""
		SELECT `date`, SUM(minutes_active) AS minutes
		FROM `tabLMS Daily Activity`
		WHERE `user` = %s AND `date` >= %s
		GROUP BY `date`
		ORDER BY `date`
		""",
		(user_id, heatmap_start),
		as_dict=True,
	)
	heatmap_by_date = {str(row.date): cint(row.minutes) for row in heatmap_rows}

	heatmap = []
	current = getdate(heatmap_start)
	end = getdate(today())
	while current <= end:
		date_str = str(current)
		minutes = heatmap_by_date.get(date_str, 0)
		heatmap.append(
			{
				"date": date_str,
				"minutes": minutes,
				"level": _heatmap_level(minutes),
			}
		)
		current = add_days(current, 1)

	return {
		"user_id": user_id,
		"summary_period_days": SUMMARY_DAYS,
		"heatmap_period_days": HEATMAP_DAYS,
		"summary_cards": summary_cards,
		"heatmap": heatmap,
	}


@frappe.whitelist()
def get_my_summary():
	"""Return the current user's time summary for the student home view."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)
	return _build_user_summary(frappe.session.user)


@frappe.whitelist()
def get_user_summary(user_id: str):
	"""Return summary cards and 90-day heatmap for a user."""
	_ensure_user_time_access(user_id)

	if not user_id or not frappe.db.exists("User", user_id):
		frappe.throw(_("User not found"))

	return _build_user_summary(user_id)


def _build_day_detail(user_id: str, date: str) -> dict:
	activity_date = getdate(date)
	rows = frappe.get_all(
		"LMS Daily Activity",
		filters={"user": user_id, "date": activity_date},
		fields=["module", "minutes_active"],
	)

	module_minutes = {m: 0 for m in MODULES}
	for row in rows:
		module_minutes[row.module] = cint(row.minutes_active)

	total_minutes = sum(module_minutes.values())

	breakdown = [
		{
			"label": "Courses",
			"minutes": module_minutes["Courses"],
			"display": _format_duration(module_minutes["Courses"]),
		},
		{
			"label": "Quizzes",
			"minutes": module_minutes["Quiz"],
			"display": _format_duration(module_minutes["Quiz"]),
		},
		{
			"label": "Library / other",
			"minutes": (
				module_minutes["Assignment"]
				+ module_minutes["Library"]
				+ module_minutes["Programming"]
				+ module_minutes["Other"]
			),
			"display": _format_duration(
				module_minutes["Assignment"]
				+ module_minutes["Library"]
				+ module_minutes["Programming"]
				+ module_minutes["Other"]
			),
		},
	]

	return {
		"user_id": user_id,
		"date": str(activity_date),
		"total_minutes": total_minutes,
		"total_display": _format_duration(total_minutes),
		"breakdown": breakdown,
	}


@frappe.whitelist()
def get_day_detail(user_id: str, date: str):
	"""Return per-module breakdown for a single day (heatmap tooltip)."""
	_ensure_user_time_access(user_id)

	if not user_id or not frappe.db.exists("User", user_id):
		frappe.throw(_("User not found"))

	if not date:
		frappe.throw(_("Date is required"))

	return _build_day_detail(user_id, date)


def _get_available_years(user_id: str) -> list[int]:
	current_year = getdate(today()).year
	return [current_year, current_year - 1, current_year - 2]


def _build_year_heatmap(user_id: str, year: int) -> dict:
	year = cint(year)
	today_date = getdate(today())
	year_start = getdate(f"{year}-01-01")
	year_end = getdate(f"{year}-12-31")

	# Cross-DB notes:
	# - Prefer an inclusive date range over YEAR(`date`) (YEAR() does not exist on Postgres).
	# - Quote `user` so Postgres does not treat bare USER as the session role keyword.
	heatmap_rows = frappe.db.sql(
		"""
		SELECT `date`, SUM(minutes_active) AS minutes
		FROM `tabLMS Daily Activity`
		WHERE `user` = %s AND `date` BETWEEN %s AND %s
		GROUP BY `date`
		ORDER BY `date`
		""",
		(user_id, year_start, year_end),
		as_dict=True,
	)
	heatmap_by_date = {str(row.date): cint(row.minutes) for row in heatmap_rows}

	heatmap = []
	total_minutes = 0
	current = year_start
	while current <= year_end:
		date_str = str(current)
		minutes = heatmap_by_date.get(date_str, 0)
		is_future = current > today_date
		if not is_future:
			total_minutes += minutes
		heatmap.append(
			{
				"date": date_str,
				"minutes": minutes,
				"level": _heatmap_level(minutes),
				"is_future": is_future,
			}
		)
		current = add_days(current, 1)

	return {
		"user_id": user_id,
		"year": year,
		"available_years": _get_available_years(user_id),
		"total_minutes": total_minutes,
		"total_display": _format_duration(total_minutes),
		"heatmap": heatmap,
	}


@frappe.whitelist()
def get_heatmap(user_id: str = None, year: int = None):
	"""Return a full-year activity heatmap for a user."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	user_id = user_id or frappe.session.user
	_ensure_user_time_access(user_id)

	if not frappe.db.exists("User", user_id):
		frappe.throw(_("User not found"))

	selected_year = cint(year) if year else getdate(today()).year
	return _build_year_heatmap(user_id, selected_year)


@frappe.whitelist()
def get_my_heatmap(year: int = None):
	"""Return the current user's full-year activity heatmap."""
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	selected_year = cint(year) if year else getdate(today()).year
	return _build_year_heatmap(frappe.session.user, selected_year)


def aggregate_daily_activity(target_date=None):
	"""Roll raw heartbeats for a day into LMS Daily Activity (nightly job)."""
	target_date = getdate(target_date) if target_date else add_days(today(), -1)

	rows = frappe.db.sql(
		"""
		SELECT `user`, role, module, COUNT(*) AS heartbeat_count, MAX(`timestamp`) AS last_heartbeat
		FROM `tabLMS Activity Heartbeat`
		WHERE DATE(`timestamp`) = %s
		GROUP BY `user`, role, module
		""",
		target_date,
		as_dict=True,
	)

	for row in rows:
		minutes_active = cint(row.heartbeat_count) * HEARTBEAT_MINUTES
		existing = frappe.db.get_value(
			"LMS Daily Activity",
			{"user": row.user, "date": target_date, "module": row.module},
		)
		if existing:
			# Use max of existing (live increments) and aggregated count
			current = cint(frappe.db.get_value("LMS Daily Activity", existing, "minutes_active"))
			frappe.db.set_value(
				"LMS Daily Activity",
				existing,
				{
					"minutes_active": max(current, minutes_active),
					"last_heartbeat": row.last_heartbeat,
					"role": row.role,
				},
				update_modified=False,
			)
		else:
			frappe.get_doc(
				{
					"doctype": "LMS Daily Activity",
					"user": row.user,
					"role": row.role,
					"date": target_date,
					"module": row.module,
					"minutes_active": minutes_active,
					"last_heartbeat": row.last_heartbeat,
				}
			).insert(ignore_permissions=True)

	frappe.db.commit()


def purge_old_heartbeats():
	"""Delete raw heartbeat logs older than retention window (weekly job)."""
	cutoff = add_days(today(), -RAW_HEARTBEAT_RETENTION_DAYS)
	old_names = frappe.get_all(
		"LMS Activity Heartbeat",
		filters=[["timestamp", "<", cutoff]],
		pluck="name",
		limit=5000,
	)
	for name in old_names:
		frappe.delete_doc("LMS Activity Heartbeat", name, ignore_permissions=True, force=True)
	if old_names:
		frappe.db.commit()
