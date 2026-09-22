# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""OJT Certification Metrics — sheet sync and analytics APIs."""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from lms.lms import access

DOCTYPE = "Sales OJT Certification Metric"
SETTINGS = "Sales OJT Certification Settings"
STAGES = [
	"Not Started",
	"Started",
	"Mock Completed",
	"Audit Completed",
	"Product Tests Completed",
]
DEFAULT_SHEET_URL = (
	"https://docs.google.com/spreadsheets/d/1rzjALRLADp4LAl0vEwYPMr1_afDUEv0Sr5gDhXjxtl4/edit?gid=0#gid=0"
)
SEED_CSV = "lms/lms/data/ojt_certification_metrics.csv"
PRODUCT_FIELDS = ("target_exam", "cbse", "test_prep", "lsq", "math_champ")
SORTABLE = {
	"employee_name": "employee_name",
	"email": "email",
	"location": "location",
	"batch_start": "batch_start",
	"attendance_days": "attendance_days",
	"ai_mock_score": "ai_mock_score",
	"audit_score": "audit_score",
	"product_avg": "product_avg",
	"stage": "stage",
	"booked": "booked",
	"catered": "catered",
}
HEADER_MAP = {
	"batch start": "batch_start",
	"employee name": "employee_name",
	"email id": "email",
	"email": "email",
	"locations": "location",
	"location": "location",
	"training manager": "training_manager",
	"attendance days": "attendance_days",
	"ai mock score": "ai_mock_score",
	"audit score (max 20)": "audit_score",
	"audit score": "audit_score",
	"dc": "dc",
	"cc": "cc",
	"tt": "talk_time",
	"booked": "booked",
	"catered": "catered",
	"target exam": "target_exam",
	"cbse": "cbse",
	"test prep": "test_prep",
	"lsq": "lsq",
	"math champ": "math_champ",
}


def make_row_key(email, batch_start) -> str:
	email = (email or "").strip().lower()
	batch = getdate(batch_start) if batch_start else ""
	return f"{email}|{batch or ''}"


def derive_product_avg(row) -> float | None:
	values = []
	for field in PRODUCT_FIELDS:
		value = _get(row, field)
		if value is None or value == "":
			continue
		values.append(flt(value))
	if not values:
		return None
	return round(sum(values) / len(values), 2)


def derive_stage(row) -> str:
	if _has_all_product_scores(row):
		return "Product Tests Completed"
	if _has_value(row, "audit_score"):
		return "Audit Completed"
	if _has_value(row, "ai_mock_score"):
		return "Mock Completed"
	if cint(_get(row, "attendance_days") or 0) > 0:
		return "Started"
	return "Not Started"


def _get(row, field):
	if isinstance(row, dict):
		return row.get(field)
	return getattr(row, field, None)


def _has_value(row, field) -> bool:
	value = _get(row, field)
	return value not in (None, "")


def _has_all_product_scores(row) -> bool:
	return all(_has_value(row, field) for field in PRODUCT_FIELDS)


def _ensure_analytics_access():
	from lms.lms.api import _ensure_analytics_access as ensure

	ensure()


def _get_settings():
	if not frappe.db.exists("DocType", SETTINGS):
		return None
	try:
		return frappe.get_single(SETTINGS)
	except Exception:
		return None


@frappe.whitelist()
def get_ojt_certification_overview():
	_ensure_analytics_access()
	settings = _get_settings()
	total = frappe.db.count(DOCTYPE)
	if not total:
		return {
			"kpis": _empty_kpis(),
			"funnel": _funnel_from_counts(0, 0, 0, 0, 0),
			"charts": {"location": [], "product_scores": [], "audit_distribution": []},
			"filters": {"locations": [], "batches": []},
			"sync": _sync_payload(settings),
		}

	started = cint(
		frappe.db.sql(
			f"select count(*) from `tab{DOCTYPE}` where ifnull(attendance_days, 0) > 0"
		)[0][0]
	)
	mock_completed = cint(
		frappe.db.sql(f"select count(*) from `tab{DOCTYPE}` where ai_mock_score is not null")[0][0]
	)
	audit_completed = cint(
		frappe.db.sql(f"select count(*) from `tab{DOCTYPE}` where audit_score is not null")[0][0]
	)
	product_completed = cint(
		frappe.db.sql(
			f"""
			select count(*) from `tab{DOCTYPE}`
			where target_exam is not null
			  and cbse is not null
			  and test_prep is not null
			  and lsq is not null
			  and math_champ is not null
			"""
		)[0][0]
	)
	not_started = max(total - started, 0)

	avg_row = frappe.db.sql(
		f"""
		select
			avg(attendance_days),
			avg(ai_mock_score),
			avg(audit_score),
			avg(product_avg)
		from `tab{DOCTYPE}`
		""",
		as_list=True,
	)[0]

	kpis = [
		{"key": "total", "label": _("Total Learners"), "value": total, "subtext": _("From OJT certification sheet")},
		{"key": "started", "label": _("Started"), "value": started, "subtext": _("Attendance days > 0")},
		{"key": "not_started", "label": _("Not Started"), "value": not_started, "subtext": _("No attendance recorded")},
		{
			"key": "audit_completed",
			"label": _("Audit Completed"),
			"value": audit_completed,
			"subtext": _("Learners with an audit score"),
		},
		{
			"key": "avg_audit",
			"label": _("Average Audit Score"),
			"value": _fmt_score(avg_row[2]),
			"subtext": _("Out of 20"),
		},
		{
			"key": "avg_product",
			"label": _("Average Product Score"),
			"value": _fmt_score(avg_row[3]),
			"subtext": _("Mean of product tests / 20"),
		},
	]

	return {
		"kpis": kpis,
		"funnel": _funnel_from_counts(total, started, mock_completed, audit_completed, product_completed),
		"charts": {
			"location": _location_chart(),
			"product_scores": _product_score_chart(),
			"audit_distribution": _audit_distribution_chart(),
		},
		"filters": {
			"locations": _location_options(),
			"batches": _batch_filter_values(),
			"stages": list(STAGES),
		},
		"sync": _sync_payload(settings),
		"averages": {
			"attendance_days": _fmt_number(avg_row[0]),
			"ai_mock_score": _fmt_score(avg_row[1]),
			"audit_score": _fmt_score(avg_row[2]),
			"product_avg": _fmt_score(avg_row[3]),
		},
	}


@frappe.whitelist()
def get_ojt_certification_learners(
	search: str | None = None,
	location: str | None = None,
	batch_start: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	funnel_stage: str | None = None,
	sort_by: str | None = None,
	sort_order: str | None = None,
	page: int = 1,
	page_length: int = 25,
):
	_ensure_analytics_access()
	page = max(cint(page) or 1, 1)
	page_length = min(max(cint(page_length) or 25, 1), 100)
	filters_sql, values = _learner_filters(
		search=search,
		location=location,
		batch_start=batch_start,
		from_date=from_date,
		to_date=to_date,
		funnel_stage=funnel_stage,
	)
	order_col = SORTABLE.get((sort_by or "").strip(), "employee_name")
	order_dir = "desc" if str(sort_order or "").lower() == "desc" else "asc"
	total = cint(
		frappe.db.sql(
			f"select count(*) from `tab{DOCTYPE}` {filters_sql}",
			values,
		)[0][0]
	)
	offset = (page - 1) * page_length
	rows = frappe.db.sql(
		f"""
		select
			name, learner, employee_name, email, location, training_manager, batch_start,
			attendance_days, ai_mock_score, audit_score, product_avg, stage,
			dc, cc, talk_time, booked, catered,
			target_exam, cbse, test_prep, lsq, math_champ
		from `tab{DOCTYPE}`
		{filters_sql}
		order by `{order_col}` {order_dir}, employee_name asc
		limit %(_limit)s offset %(_offset)s
		""",
		{**values, "_limit": page_length, "_offset": offset},
		as_dict=True,
	)
	start = 0 if total == 0 else offset + 1
	end = min(offset + len(rows), total)
	return {
		"rows": rows,
		"page": page,
		"page_length": page_length,
		"total": total,
		"start": start,
		"end": end,
		"total_pages": max(((total + page_length - 1) // page_length), 1) if total else 1,
	}


@frappe.whitelist()
def get_ojt_certification_learner_detail(name: str):
	_ensure_analytics_access()
	if not name or not frappe.db.exists(DOCTYPE, name):
		frappe.throw(_("Learner record not found"))
	doc = frappe.get_doc(DOCTYPE, name)
	return {
		"name": doc.name,
		"learner": doc.learner,
		"employee_name": doc.employee_name,
		"email": doc.email,
		"location": doc.location,
		"training_manager": doc.training_manager,
		"batch_start": doc.batch_start,
		"attendance_days": doc.attendance_days,
		"ai_mock_score": doc.ai_mock_score,
		"audit_score": doc.audit_score,
		"product_avg": doc.product_avg,
		"stage": doc.stage,
		"dc": doc.dc,
		"cc": doc.cc,
		"talk_time": doc.talk_time,
		"booked": doc.booked,
		"catered": doc.catered,
		"target_exam": doc.target_exam,
		"cbse": doc.cbse,
		"test_prep": doc.test_prep,
		"lsq": doc.lsq,
		"math_champ": doc.math_champ,
	}


@frappe.whitelist()
def search_ojt_learners(search: str | None = None):
	"""Search registered LMS users for the Add Learner Report picker."""
	_ensure_analytics_access()
	term = (search or "").strip()
	has_city = frappe.db.has_column("User", "city")
	fields = ["name", "full_name", "email"]
	if has_city:
		fields.append("city")
	filters = {"enabled": 1, "name": ["!=", "Guest"]}
	kwargs = {
		"filters": filters,
		"fields": fields,
		"order_by": "full_name asc",
		"limit": 40,
	}
	if term:
		kwargs["or_filters"] = [
			["full_name", "like", f"%{term}%"],
			["email", "like", f"%{term}%"],
			["name", "like", f"%{term}%"],
		]
	users = frappe.get_all("User", **kwargs)
	return [
		{
			"value": user.name,
			"label": user.full_name or user.name,
			"description": user.email or user.name,
			"email": user.email or user.name,
			"city": user.city if has_city else None,
		}
		for user in users
	]


@frappe.whitelist()
def get_ojt_report_options():
	"""Locations and stages for admin add/edit forms and filters."""
	_ensure_analytics_access()
	return {
		"locations": _location_options(),
		"stages": STAGES,
	}


@frappe.whitelist()
def save_ojt_certification_report(
	name: str | None = None,
	learner: str | None = None,
	location: str | None = None,
	batch_start: str | None = None,
	attendance_days=None,
	ai_mock_score=None,
	audit_score=None,
	product_avg=None,
	stage: str | None = None,
):
	"""Create or update an OJT certification report linked to an LMS user."""
	_ensure_analytics_access()
	user = None
	email = None
	if learner:
		if not frappe.db.exists("User", learner):
			frappe.throw(_("Select a registered learner"))
		user = frappe.db.get_value(
			"User",
			learner,
			["name", "full_name", "email"],
			as_dict=True,
		)
		email = (user.email or user.name or "").strip().lower()
		if not email:
			frappe.throw(_("The selected learner does not have an email address"))
	elif not name:
		frappe.throw(_("Select a registered learner"))

	parsed_batch = getdate(batch_start) if batch_start else None
	existing = None
	if email:
		row_key = make_row_key(email, parsed_batch)
		existing = frappe.db.get_value(DOCTYPE, {"row_key": row_key}, "name")
	if name:
		if not frappe.db.exists(DOCTYPE, name):
			frappe.throw(_("Learner record not found"))
		doc = frappe.get_doc(DOCTYPE, name)
		if existing and existing != name:
			frappe.throw(_("A report already exists for this learner and batch start date"))
	elif existing:
		doc = frappe.get_doc(DOCTYPE, existing)
	else:
		doc = frappe.new_doc(DOCTYPE)

	if user:
		doc.learner = learner
		doc.employee_name = user.full_name or user.name
		doc.email = email
	doc.location = (location or "").strip() or None
	doc.batch_start = parsed_batch
	doc.attendance_days = _optional_int(attendance_days)
	doc.ai_mock_score = _optional_float(ai_mock_score)
	doc.audit_score = _optional_float(audit_score)
	doc.product_avg = _optional_float(product_avg)
	doc.stage = (stage or "").strip() or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name}


def _optional_int(value):
	if value in (None, ""):
		return None
	return cint(value)


def _optional_float(value):
	if value in (None, ""):
		return None
	return flt(value)


@frappe.whitelist()
def export_ojt_certification_report(
	search: str | None = None,
	location: str | None = None,
	batch_start: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	funnel_stage: str | None = None,
	sort_by: str | None = None,
	sort_order: str | None = None,
):
	"""Return filtered learner rows as CSV for download. Caps at 50,000 rows."""
	_ensure_analytics_access()
	filters_sql, values = _learner_filters(
		search=search,
		location=location,
		batch_start=batch_start,
		from_date=from_date,
		to_date=to_date,
		funnel_stage=funnel_stage,
	)
	order_col = SORTABLE.get((sort_by or "").strip(), "employee_name")
	order_dir = "desc" if str(sort_order or "").lower() == "desc" else "asc"
	rows = frappe.db.sql(
		f"""
		select
			employee_name, email, location, training_manager, batch_start,
			attendance_days, ai_mock_score, audit_score, product_avg, stage,
			dc, cc, talk_time, booked, catered,
			target_exam, cbse, test_prep, lsq, math_champ
		from `tab{DOCTYPE}`
		{filters_sql}
		order by `{order_col}` {order_dir}, employee_name asc
		limit 50000
		""",
		values,
		as_dict=True,
	)
	output = io.StringIO()
	fieldnames = [
		"Learner Name",
		"Email ID",
		"Location",
		"Batch Start",
		"Attendance",
		"AI Mock",
		"Audit / 20",
		"Product avg / 20",
		"Stage",
	]
	writer = csv.DictWriter(output, fieldnames=fieldnames)
	writer.writeheader()
	for row in rows:
		writer.writerow(
			{
				"Learner Name": row.get("employee_name") or "",
				"Email ID": row.get("email") or "",
				"Location": row.get("location") or "",
				"Batch Start": _format_display_date(row.get("batch_start")),
				"Attendance": row.get("attendance_days") if row.get("attendance_days") is not None else "",
				"AI Mock": row.get("ai_mock_score") if row.get("ai_mock_score") is not None else "",
				"Audit / 20": row.get("audit_score") if row.get("audit_score") is not None else "",
				"Product avg / 20": row.get("product_avg") if row.get("product_avg") is not None else "",
				"Stage": row.get("stage") or "",
			}
		)
	return {
		"filename": "ojt-certification-report.csv",
		"csv": output.getvalue(),
		"count": len(rows),
	}


@frappe.whitelist()
def sync_ojt_certification_metrics(sheet_url: str | None = None):
	"""Fetch the Google Sheet and replace stored learner rows. No fake success."""
	# Syncing replaces everyone's OJT data, and a caller-supplied URL decides where it comes from.
	# That is an org-wide action, so it stays with Super Admins rather than every instructor.
	if not access.is_super_admin():
		frappe.throw(_("Only a Super Admin can sync the OJT certification sheet."), frappe.PermissionError)
	settings = frappe.get_single(SETTINGS)
	url = (sheet_url or settings.sheet_url or DEFAULT_SHEET_URL).strip()
	if sheet_url:
		settings.sheet_url = url
	try:
		csv_text = _fetch_google_sheet_csv(url)
		rows = parse_ojt_certification_csv(csv_text)
		if not rows:
			raise frappe.ValidationError(_("No learner rows found in the sheet."))
		saved = replace_ojt_certification_rows(rows)
		settings.last_synced = now_datetime()
		settings.last_sync_source = "Google Sheet"
		settings.last_sync_status = "Success"
		settings.row_count = saved
		settings.last_sync_message = _("Synced {0} learners from Google Sheet.").format(saved)
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"ok": True,
			"imported": saved,
			"sync": _sync_payload(settings),
		}
	except Exception as exc:
		# Throw away everything this sync wrote before recording the failure, so a sheet that breaks
		# halfway can't leave learners' rows missing.
		frappe.db.rollback()
		settings = frappe.get_single(SETTINGS)
		settings.last_sync_status = "Failed"
		settings.last_sync_message = str(exc)[:500]
		settings.save(ignore_permissions=True)
		frappe.db.commit()
		frappe.throw(_("Could not sync OJT certification sheet: {0}").format(str(exc)))


def seed_ojt_certification_metrics_if_empty():
	"""Load the attached sheet snapshot once, only when the table is empty."""
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	if frappe.db.count(DOCTYPE):
		return
	path = frappe.get_app_path("lms", "lms", "data", "ojt_certification_metrics.csv")
	with open(path, encoding="utf-8") as handle:
		rows = parse_ojt_certification_csv(handle.read())
	saved = replace_ojt_certification_rows(rows)
	if frappe.db.exists("DocType", SETTINGS):
		settings = frappe.get_single(SETTINGS)
		if not settings.sheet_url:
			settings.sheet_url = DEFAULT_SHEET_URL
		settings.last_synced = now_datetime()
		settings.last_sync_source = "Attached sheet snapshot"
		settings.last_sync_status = "Success"
		settings.row_count = saved
		settings.last_sync_message = _("Loaded {0} learners from the attached OJT sheet.").format(saved)
		settings.save(ignore_permissions=True)
	frappe.db.commit()
	return saved


def parse_ojt_certification_csv(text: str) -> list[dict]:
	sample = text.lstrip("\ufeff")
	reader = csv.reader(io.StringIO(sample))
	rows = [row for row in reader]
	header_idx, mapping = _find_header(rows)
	if header_idx is None:
		frappe.throw(_("Could not find a header row with Employee Name / Email ID."))
	parsed = []
	for raw in rows[header_idx + 1 :]:
		if not any(str(cell).strip() for cell in raw):
			continue
		item = {}
		for index, field in mapping.items():
			value = raw[index].strip() if index < len(raw) and raw[index] is not None else ""
			item[field] = _coerce_field(field, value)
		if not item.get("employee_name") and not item.get("email"):
			continue
		if not item.get("email"):
			continue
		item["email"] = item["email"].lower()
		item["product_avg"] = derive_product_avg(item)
		item["stage"] = derive_stage(item)
		item["row_key"] = make_row_key(item["email"], item.get("batch_start"))
		parsed.append(item)
	return parsed


def replace_ojt_certification_rows(rows: list[dict]) -> int:
	"""Bring stored rows in line with the sheet.

	Rows are updated in place by `row_key` rather than deleted and re-inserted, so a bad sheet can
	never leave the table half empty, and anything the sheet doesn't carry (manual edits to other
	fields) survives. Rows that have left the sheet are removed only after every other row landed.
	"""
	# The sheet can repeat a learner+batch; the last row wins. Duplicates used to break the insert
	# halfway through, after the whole table had already been deleted.
	unique: dict[str, dict] = {}
	for item in rows:
		key = item.get("row_key")
		if key:
			unique[key] = item

	for key, item in unique.items():
		email = (item.get("email") or "").strip().lower()
		if email:
			user = frappe.db.get_value("User", {"email": email}, "name")
			if not user and frappe.db.exists("User", email):
				user = email
			if not user:
				# The learner may have moved to a work email since the sheet was written.
				user = _user_by_former_email(email)
			if user:
				item["learner"] = user
				item["email"] = frappe.db.get_value("User", user, "email") or email
				item["row_key"] = make_row_key(item["email"], item.get("batch_start"))
		existing = frappe.db.exists(DOCTYPE, {"row_key": key})
		doc = frappe.get_doc(DOCTYPE, existing) if existing else frappe.new_doc(DOCTYPE)
		doc.update(item)
		doc.flags.from_sheet_sync = True
		doc.save(ignore_permissions=True) if existing else doc.insert(ignore_permissions=True)

	keys = list(unique)
	stale = frappe.get_all(DOCTYPE, filters={"row_key": ["not in", keys]}, pluck="name") if keys else []
	for name in stale:
		frappe.delete_doc(DOCTYPE, name, ignore_permissions=True, force=True, delete_permanently=True)
	return len(unique)


def _user_by_former_email(email: str) -> str | None:
	"""Follow an email change: the sheet may still hold someone's old personal address."""
	if not frappe.db.exists("DocType", "LMS Identity Change"):
		return None
	changed = frappe.get_all(
		"LMS Identity Change",
		filters={"field": "Email", "old_value": email},
		fields=["new_value"],
		order_by="changed_on desc",
		limit=1,
	)
	if changed and frappe.db.exists("User", changed[0].new_value):
		return changed[0].new_value
	return None


def _find_header(rows):
	for idx, row in enumerate(rows[:15]):
		normalized = [_normalize_header(cell) for cell in row]
		if "employee name" in normalized and ("email id" in normalized or "email" in normalized):
			mapping = {}
			for col, header in enumerate(normalized):
				field = HEADER_MAP.get(header)
				if field:
					mapping[col] = field
			return idx, mapping
	return None, {}


def _normalize_header(value: str) -> str:
	return re.sub(r"\s+", " ", (value or "").strip().lower())


def _coerce_field(field: str, value: str):
	if value in ("", None):
		return None
	if field == "batch_start":
		return _parse_date(value)
	if field in {
		"attendance_days",
		"dc",
		"cc",
		"booked",
		"catered",
	}:
		return cint(_numeric(value))
	if field in {
		"ai_mock_score",
		"audit_score",
		"target_exam",
		"cbse",
		"test_prep",
		"lsq",
		"math_champ",
	}:
		return flt(_numeric(value))
	return value


def _numeric(value: str):
	cleaned = str(value).replace(",", "").strip()
	match = re.search(r"-?\d+(\.\d+)?", cleaned)
	return match.group(0) if match else 0


def _parse_date(value: str):
	text = (value or "").strip()
	if not text:
		return None
	for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
		try:
			return datetime.strptime(text, fmt).date()
		except ValueError:
			continue
	try:
		return getdate(text)
	except Exception:
		return None


def _fetch_google_sheet_csv(url: str) -> str:
	sheet_id, gid = _parse_sheet_url(url)
	if not sheet_id:
		frappe.throw(_("Invalid Google Sheet URL."))
	candidates = [
		f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
		f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
	]
	last_error = None
	for candidate in candidates:
		try:
			request = urllib.request.Request(
				candidate,
				headers={"User-Agent": "SalesLMS/1.0"},
			)
			with urllib.request.urlopen(request, timeout=30) as response:
				text = response.read().decode("utf-8", errors="replace")
			if text.strip().startswith("<"):
				last_error = _("Google Sheet is not publicly accessible as CSV.")
				continue
			if "Employee Name" in text or "employee name" in text.lower() or "Email ID" in text:
				return text
			return text
		except Exception as exc:
			last_error = str(exc)
			continue
	frappe.throw(last_error or _("Unable to download the Google Sheet."))


def _parse_sheet_url(url: str):
	parsed = urlparse(url or "")
	match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", parsed.path or url)
	sheet_id = match.group(1) if match else None
	query = parse_qs(parsed.query)
	fragment = parse_qs((parsed.fragment or "").replace("?", "&"))
	gid = "0"
	if query.get("gid"):
		gid = query["gid"][0]
	elif fragment.get("gid"):
		gid = fragment["gid"][0]
	return sheet_id, gid


def _learner_filters(
	search=None,
	location=None,
	batch_start=None,
	from_date=None,
	to_date=None,
	funnel_stage=None,
):
	clauses = []
	values = {}
	term = (search or "").strip()
	if term:
		clauses.append(
			"(employee_name like %(search)s or email like %(search)s or ifnull(training_manager,'') like %(search)s)"
		)
		values["search"] = f"%{term}%"
	if location and location not in ("", "__all__"):
		clauses.append("location = %(location)s")
		values["location"] = location
	if batch_start and batch_start not in ("", "__all__"):
		clauses.append("batch_start = %(batch_start)s")
		values["batch_start"] = getdate(batch_start)
	if from_date:
		clauses.append("batch_start >= %(from_date)s")
		values["from_date"] = getdate(from_date)
	if to_date:
		clauses.append("batch_start <= %(to_date)s")
		values["to_date"] = getdate(to_date)
	stage = (funnel_stage or "").strip()
	if stage == "started":
		clauses.append("ifnull(attendance_days, 0) > 0")
	elif stage == "mock_completed":
		clauses.append("ai_mock_score is not null")
	elif stage == "audit_completed":
		clauses.append("audit_score is not null")
	elif stage == "product_tests_completed":
		clauses.append(
			"target_exam is not null and cbse is not null and test_prep is not null and lsq is not null and math_champ is not null"
		)
	elif stage == "not_started":
		clauses.append("ifnull(attendance_days, 0) = 0")
	where = f"where {' and '.join(clauses)}" if clauses else ""
	return where, values


def _funnel_from_counts(total, started, mock_completed, audit_completed, product_completed):
	return [
		{"key": "total", "label": _("Total Learners"), "value": total},
		{"key": "started", "label": _("Started Training"), "value": started},
		{"key": "mock_completed", "label": _("AI Mock Completed"), "value": mock_completed},
		{"key": "audit_completed", "label": _("Audit Completed"), "value": audit_completed},
		{"key": "product_tests_completed", "label": _("Product Tests Completed"), "value": product_completed},
	]


def _location_chart():
	rows = frappe.db.sql(
		f"""
		select ifnull(nullif(location, ''), 'Unspecified') as label, count(*) as value
		from `tab{DOCTYPE}`
		group by label
		order by value desc, label asc
		""",
		as_dict=True,
	)
	return rows


def _product_score_chart():
	row = frappe.db.sql(
		f"""
		select
			avg(target_exam) as target_exam,
			avg(cbse) as cbse,
			avg(test_prep) as test_prep,
			avg(lsq) as lsq,
			avg(math_champ) as math_champ
		from `tab{DOCTYPE}`
		""",
		as_dict=True,
	)[0]
	return [
		{"label": _("Target Exam"), "value": _fmt_number(row.get("target_exam"))},
		{"label": _("CBSE"), "value": _fmt_number(row.get("cbse"))},
		{"label": _("Test Prep"), "value": _fmt_number(row.get("test_prep"))},
		{"label": _("LSQ"), "value": _fmt_number(row.get("lsq"))},
		{"label": _("Math Champ"), "value": _fmt_number(row.get("math_champ"))},
	]


def _audit_distribution_chart():
	rows = frappe.db.sql(
		f"""
		select
			case
				when audit_score is null then 'No score'
				when audit_score < 10 then '0–9'
				when audit_score < 15 then '10–14'
				when audit_score < 18 then '15–17'
				else '18–20'
			end as label,
			count(*) as value
		from `tab{DOCTYPE}`
		group by label
		""",
		as_dict=True,
	)
	order = ["No score", "0–9", "10–14", "15–17", "18–20"]
	by_label = {row.label: cint(row.value) for row in rows}
	return [{"label": label, "value": by_label.get(label, 0)} for label in order if by_label.get(label, 0)]


def _format_display_date(value):
	if not value:
		return ""
	parsed = getdate(value)
	return parsed.strftime("%d %b %Y")


def _filter_values(field):
	rows = frappe.db.sql(
		f"""
		select distinct {field} as value
		from `tab{DOCTYPE}`
		where ifnull({field}, '') != ''
		order by value asc
		""",
		as_dict=True,
	)
	return [row.value for row in rows]


def _location_options():
	locations = set(_filter_values("location"))
	if frappe.db.has_column("User", "city"):
		for row in frappe.get_all(
			"User",
			filters={"enabled": 1},
			fields=["city"],
			distinct=True,
		):
			if row.city:
				locations.add(row.city)
	return sorted(locations)


def _batch_filter_values():
	rows = frappe.db.sql(
		f"""
		select distinct batch_start as value
		from `tab{DOCTYPE}`
		where batch_start is not null
		order by batch_start desc
		""",
		as_dict=True,
	)
	return [str(row.value) for row in rows]


def _sync_payload(settings):
	if not settings:
		return {
			"sheet_url": DEFAULT_SHEET_URL,
			"last_synced": None,
			"last_sync_source": None,
			"last_sync_status": None,
			"last_sync_message": None,
			"row_count": 0,
		}
	return {
		"sheet_url": settings.sheet_url,
		"last_synced": settings.last_synced,
		"last_sync_source": settings.last_sync_source,
		"last_sync_status": settings.last_sync_status,
		"last_sync_message": settings.last_sync_message,
		"row_count": settings.row_count,
	}


def _empty_kpis():
	return [
		{"key": "total", "label": _("Total Learners"), "value": 0, "subtext": _("No sheet data yet")},
		{"key": "started", "label": _("Started"), "value": 0, "subtext": _("Attendance days > 0")},
		{"key": "not_started", "label": _("Not Started"), "value": 0, "subtext": _("No attendance recorded")},
		{"key": "audit_completed", "label": _("Audit Completed"), "value": 0, "subtext": _("Learners with an audit score")},
		{"key": "avg_audit", "label": _("Average Audit Score"), "value": "—", "subtext": _("Out of 20")},
		{"key": "avg_product", "label": _("Average Product Score"), "value": "—", "subtext": _("Mean of product tests / 20")},
	]


def _fmt_score(value):
	if value is None:
		return "—"
	return f"{flt(value, 1):.1f}"


def _fmt_number(value):
	if value is None:
		return 0
	return round(flt(value), 1)


ATTENDANCE_CSV_FIELDS = (
	"email",
	"batch_start",
	"attendance_days",
	"dc",
	"cc",
	"talk_time",
	"booked",
	"catered",
)


def _parse_attendance_csv_rows(text: str) -> list[dict]:
	sample = text.lstrip("\ufeff")
	reader = csv.reader(io.StringIO(sample))
	rows = [row for row in reader]
	if not rows:
		return []
	header = [_normalize_header(cell) for cell in rows[0]]
	alias = {
		"email": "email",
		"batch start": "batch_start",
		"batch_start": "batch_start",
		"attendance days": "attendance_days",
		"attendance_days": "attendance_days",
		"dc": "dc",
		"cc": "cc",
		"talk time": "talk_time",
		"talk_time": "talk_time",
		"booked": "booked",
		"catered": "catered",
	}
	field_indexes = {}
	for idx, label in enumerate(header):
		field = alias.get(label)
		if field:
			field_indexes[field] = idx
	required = {"email", "batch_start"}
	if not required.issubset(field_indexes.keys()):
		frappe.throw(
			_("CSV must include columns: email, batch_start, attendance_days, dc, cc, talk_time, booked, catered.")
		)
	parsed = []
	for raw in rows[1:]:
		if not any(str(cell).strip() for cell in raw):
			continue
		item = {}
		for field, index in field_indexes.items():
			value = raw[index].strip() if index < len(raw) and raw[index] is not None else ""
			item[field] = _coerce_field(field, value) if value != "" else None
		email = (item.get("email") or "").strip().lower()
		if not email or not item.get("batch_start"):
			continue
		item["email"] = email
		item["row_key"] = make_row_key(email, item.get("batch_start"))
		parsed.append(item)
	return parsed


def _validate_attendance_import_rows(rows: list[dict]) -> dict:
	errors = []
	warnings = []
	seen = {}
	preview = []
	for line_no, row in enumerate(rows, start=2):
		row_errors = []
		email = row.get("email")
		if not email:
			row_errors.append(_("Email is required."))
		if not row.get("batch_start"):
			row_errors.append(_("batch_start is required."))
		key = row.get("row_key")
		if key in seen:
			warnings.append(
				_("Row {0}: duplicate email + batch_start; row {1} will be replaced by this row.").format(
					line_no, seen[key]
				)
			)
		seen[key] = line_no
		if not frappe.db.exists(DOCTYPE, {"row_key": key}):
			row_errors.append(_("No OJT Certification Metric row found for this email and batch_start."))
		if row_errors:
			errors.append({"row": line_no, "email": email, "messages": row_errors})
		else:
			preview.append(
				{
					"row": line_no,
					"email": email,
					"batch_start": str(row.get("batch_start")),
					"attendance_days": row.get("attendance_days"),
					"dc": row.get("dc"),
					"cc": row.get("cc"),
					"talk_time": row.get("talk_time"),
					"booked": row.get("booked"),
					"catered": row.get("catered"),
				}
			)
	return {"errors": errors, "warnings": warnings, "preview": preview, "valid_count": len(preview)}


@frappe.whitelist()
def preview_attendance_metrics_csv(file_content: str):
	_ensure_analytics_access()
	rows = _parse_attendance_csv_rows(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the CSV."))
	result = _validate_attendance_import_rows(rows)
	result["total_rows"] = len(rows)
	return result


@frappe.whitelist()
def import_attendance_metrics_csv(file_content: str):
	_ensure_analytics_access()
	rows = _parse_attendance_csv_rows(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the CSV."))
	validation = _validate_attendance_import_rows(rows)
	if validation["errors"]:
		frappe.throw(_("Fix CSV errors before import."))

	by_key = {}
	for row in rows:
		by_key[row["row_key"]] = row

	updated = 0
	for row_key, row in by_key.items():
		name = frappe.db.get_value(DOCTYPE, {"row_key": row_key})
		if not name:
			continue
		doc = frappe.get_doc(DOCTYPE, name)
		for field in ATTENDANCE_CSV_FIELDS:
			if field in ("email", "batch_start"):
				continue
			if field in row and row[field] is not None:
				doc.set(field, row[field])
		doc.save(ignore_permissions=True)
		updated += 1

	frappe.db.commit()
	return {"updated": updated, "warnings": validation["warnings"]}
