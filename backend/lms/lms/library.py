"""Business logic for the LMS Recording Library."""

import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, now_datetime

from lms.lms.google_drive import (
	get_linked_email,
	list_recordings_from_drive,
)

SYNC_COOLDOWN_MINUTES = 5
SYNC_INTERVAL_HOURS = 6
POST_CLASS_SYNC_MINUTES = 45


def get_batch_code(batch_title: str) -> str:
	"""Extract a batch search code (e.g. B28, B2B) from the batch title."""
	if not batch_title:
		return ""
	title = batch_title.strip()
	match = re.search(r"\b([Bb]\d+[A-Za-z]*)\b", title)
	if match:
		return match.group(1).upper()
	if " - " in title:
		return title.split(" - ", 1)[0].strip()
	return title


def format_recording_row(doc) -> dict:
	batch_title = frappe.db.get_value("LMS Batch", doc.batch, "title") if doc.batch else None
	return {
		"name": doc.name,
		"batch": doc.batch,
		"batch_title": batch_title,
		"gmail_account": doc.gmail_account,
		"title": doc.title,
		"recording_date": doc.recording_date,
		"recording_time": doc.recording_time,
		"duration_minutes": doc.duration_minutes,
		"file_size_mb": doc.file_size_mb,
		"session_number": doc.session_number,
		"watch_url": doc.watch_url,
		"thumbnail_url": doc.thumbnail_url,
		"synced_at": doc.synced_at,
		"is_archived": doc.is_archived,
		"is_unavailable": doc.is_unavailable,
	}


def get_user_google_calendars(user: str | None = None) -> list[dict]:
	user = user or frappe.session.user
	meet_settings = frappe.get_all(
		"LMS Google Meet Settings",
		filters={"member": user, "enabled": 1},
		fields=["name", "google_calendar", "account_name"],
	)
	calendars = []
	seen = set()
	for row in meet_settings:
		if not row.google_calendar or row.google_calendar in seen:
			continue
		seen.add(row.google_calendar)
		calendars.append(row)
	return calendars


def get_primary_google_calendar(user: str | None = None) -> str | None:
	calendars = get_user_google_calendars(user)
	return calendars[0].google_calendar if calendars else None


def archive_recordings_for_account(gmail_account: str, exclude_batch: str | None = None):
	filters = {"gmail_account": gmail_account, "is_archived": 0}
	if exclude_batch:
		filters["batch"] = ["!=", exclude_batch]
	frappe.db.set_value("LMS Recording", filters, "is_archived", 1)


def _parse_drive_created_time(created_time: str) -> tuple[str, str]:
	dt = get_datetime(created_time)
	return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")


def _duration_minutes_from_metadata(metadata: dict | None) -> int:
	if not metadata:
		return 0
	millis = cint(metadata.get("durationMillis") or 0)
	return max(0, round(millis / 60000))


def _file_size_mb(size_bytes) -> float:
	if not size_bytes:
		return 0
	return flt(size_bytes) / (1024 * 1024)


def upsert_recording_from_drive_file(
	file_data: dict,
	batch: str,
	gmail_account: str,
) -> str | None:
	drive_file_id = file_data.get("id")
	if not drive_file_id:
		return None

	existing = frappe.db.get_value("LMS Recording", {"drive_file_id": drive_file_id})
	recording_date, recording_time = _parse_drive_created_time(file_data.get("createdTime", ""))
	values = {
		"batch": batch,
		"gmail_account": gmail_account,
		"title": file_data.get("name") or drive_file_id,
		"recording_date": recording_date,
		"recording_time": recording_time,
		"duration_minutes": _duration_minutes_from_metadata(file_data.get("videoMediaMetadata")),
		"file_size_mb": _file_size_mb(file_data.get("size")),
		"watch_url": file_data.get("webViewLink"),
		"thumbnail_url": file_data.get("thumbnailLink"),
		"synced_at": now_datetime(),
		"is_archived": 0,
		"is_unavailable": 0,
	}

	if existing:
		doc = frappe.get_doc("LMS Recording", existing)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc.name

	doc = frappe.get_doc({"doctype": "LMS Recording", "drive_file_id": drive_file_id, **values})
	doc.insert(ignore_permissions=True)
	return doc.name


def assign_session_numbers(batch: str):
	recordings = frappe.get_all(
		"LMS Recording",
		filters={"batch": batch, "is_archived": 0},
		fields=["name"],
		order_by="recording_date asc, recording_time asc, creation asc",
	)
	for index, row in enumerate(recordings, start=1):
		frappe.db.set_value("LMS Recording", row.name, "session_number", index)


def sync_batch_recordings(batch_name: str, google_calendar_name: str, gmail_account: str) -> int:
	batch = frappe.get_doc("LMS Batch", batch_name)
	batch_code = get_batch_code(batch.title)
	if not batch_code:
		return 0

	start_date = batch.start_date
	end_date = batch.end_date or add_days(batch.start_date, 21)
	synced = 0
	page_token = None

	while True:
		result = list_recordings_from_drive(
			google_calendar_name,
			batch_code,
			str(start_date),
			str(end_date),
			page_token=page_token,
		)
		for file_data in result.get("files", []):
			if upsert_recording_from_drive_file(file_data, batch_name, gmail_account):
				synced += 1

		page_token = result.get("nextPageToken")
		if not page_token:
			break

	assign_session_numbers(batch_name)
	return synced


def sync_recordings_for_user(user: str | None = None, batch_name: str | None = None) -> dict:
	user = user or frappe.session.user
	calendars = get_user_google_calendars(user)
	if not calendars:
		return {"synced": 0, "message": _("No linked Google account found.")}

	total_synced = 0
	linked_emails = []

	for calendar_row in calendars:
		gmail_account = get_linked_email(calendar_row.google_calendar) or ""
		linked_emails.append(gmail_account)

		batch_filters = {"published": 1, "google_meet_account": calendar_row.name}
		if batch_name:
			batch_filters["name"] = batch_name

		batches = frappe.get_all("LMS Batch", filters=batch_filters, pluck="name")
		for batch in batches:
			total_synced += sync_batch_recordings(batch, calendar_row.google_calendar, gmail_account)

	frappe.cache.set_value(f"lms_library_last_sync:{user}", now_datetime())
	return {
		"synced": total_synced,
		"linked_email": linked_emails[0] if linked_emails else None,
		"last_synced": now_datetime(),
	}


def _manual_sync_cooldown_seconds() -> int:
	if frappe.conf.get("developer_mode"):
		return 30
	return SYNC_COOLDOWN_MINUTES * 60


def can_manual_sync(user: str | None = None) -> tuple[bool, int]:
	user = user or frappe.session.user
	last_sync = frappe.cache.get_value(f"lms_library_manual_sync:{user}")
	if not last_sync:
		return True, 0

	elapsed = (now_datetime() - get_datetime(last_sync)).total_seconds()
	remaining = _manual_sync_cooldown_seconds() - elapsed
	if remaining > 0:
		return False, int(remaining)
	return True, 0


def mark_manual_sync(user: str | None = None):
	user = user or frappe.session.user
	frappe.cache.set_value(f"lms_library_manual_sync:{user}", now_datetime(), expires_in_sec=3600)


def scheduled_sync_all_recordings():
	last_run = frappe.cache.get_value("lms_library_scheduled_sync")
	if last_run:
		elapsed_hours = (now_datetime() - get_datetime(last_run)).total_seconds() / 3600
		if elapsed_hours < SYNC_INTERVAL_HOURS:
			return

	accounts = frappe.get_all(
		"LMS Google Meet Settings",
		filters={"enabled": 1},
		fields=["member", "name"],
	)
	for account in accounts:
		try:
			frappe.set_user(account.member)
			sync_recordings_for_user(account.member)
		except Exception:
			frappe.log_error(title=f"Library scheduled sync failed for {account.member}")
		finally:
			frappe.set_user("Administrator")

	frappe.cache.set_value("lms_library_scheduled_sync", now_datetime())


def sync_after_recent_classes():
	"""Sync batches whose live classes ended ~45 minutes ago."""
	now = now_datetime()
	window_start = now - timedelta(minutes=75)
	window_end = now - timedelta(minutes=30)

	live_classes = frappe.get_all(
		"LMS Live Class",
		filters={
			"batch_name": ["is", "set"],
			"date": ["between", [window_start.date(), now.date()]],
		},
		fields=["name", "batch_name", "date", "time", "duration", "host"],
	)

	for live_class in live_classes:
		start = get_datetime(f"{live_class.date} {live_class.time}")
		end = start + timedelta(minutes=cint(live_class.duration or 0))
		if not (window_start <= end <= window_end):
			continue

		batch = live_class.batch_name
		google_meet_account = frappe.db.get_value("LMS Batch", batch, "google_meet_account")
		if not google_meet_account:
			continue

		calendar = frappe.db.get_value("LMS Google Meet Settings", google_meet_account, "google_calendar")
		member = frappe.db.get_value("LMS Google Meet Settings", google_meet_account, "member")
		if not calendar or not member:
			continue

		try:
			frappe.set_user(member)
			gmail_account = get_linked_email(calendar) or ""
			sync_batch_recordings(batch, calendar, gmail_account)
		except Exception:
			frappe.log_error(title=f"Post-class library sync failed for {live_class.name}")
		finally:
			frappe.set_user("Administrator")


def handle_google_account_change_hook(doc, method=None):
	changed = getattr(doc, "has_value_changed", lambda _field: False)
	if changed("refresh_token") or changed("authorization_code"):
		handle_google_account_change(doc.name)


def handle_google_account_change(google_calendar_name: str):
	"""Archive recordings from the previous account email and trigger a full sync."""
	gmail_account = get_linked_email(google_calendar_name)
	if not gmail_account:
		return

	cache_key = f"lms_library_synced_email:{google_calendar_name}"
	previous_email = frappe.cache.get_value(cache_key)
	if previous_email and previous_email != gmail_account:
		archive_recordings_for_account(previous_email)

	frappe.cache.set_value(cache_key, gmail_account)

	meet_accounts = frappe.get_all(
		"LMS Google Meet Settings",
		filters={"google_calendar": google_calendar_name, "enabled": 1},
		fields=["member"],
	)
	for account in meet_accounts:
		try:
			frappe.set_user(account.member)
			sync_recordings_for_user(account.member)
		except Exception:
			frappe.log_error(title=f"Library account-change sync failed for {account.member}")
		finally:
			frappe.set_user("Administrator")


def get_accessible_batches_for_learner(user: str) -> list[str]:
	enrolled_batches = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"member": user},
		pluck="batch",
		distinct=True,
	)
	if not enrolled_batches:
		return []

	published_batches = frappe.get_all(
		"LMS Batch",
		filters={
			"name": ["in", enrolled_batches],
			"published": 1,
			"allow_recording_library": 1,
		},
		pluck="name",
	)
	return [batch for batch in published_batches if batch]


def get_accessible_batches_for_user(user: str) -> list[dict]:
	roles = set(frappe.get_roles(user))
	is_staff = not roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator"})

	if is_staff:
		return frappe.get_all(
			"LMS Batch",
			filters={"published": 1, "allow_recording_library": 1},
			fields=["name", "title"],
			order_by="title asc",
		)

	batch_names = get_accessible_batches_for_learner(user)
	if not batch_names:
		return []

	return frappe.get_all(
		"LMS Batch",
		filters={"name": ["in", batch_names]},
		fields=["name", "title"],
		order_by="title asc",
	)


def build_recording_filters(
	user: str,
	batch_id: str | None = None,
	search: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	duration: str | None = None,
	include_archived: bool = False,
) -> dict:
	filters = {}
	if not include_archived:
		filters["is_archived"] = 0

	roles = set(frappe.get_roles(user))
	is_staff = not roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator"})

	if is_staff:
		if batch_id:
			filters["batch"] = batch_id
	else:
		from lms.lms.library_assignments import get_assigned_recording_ids

		assigned_recordings = get_assigned_recording_ids(user)
		if not assigned_recordings:
			filters["name"] = ["in", []]
		else:
			filters["name"] = ["in", assigned_recordings]

		if batch_id:
			allowed_batches = get_accessible_batches_for_learner(user)
			if batch_id not in allowed_batches:
				frappe.throw(_("You are not permitted to view recordings for this batch."), frappe.PermissionError)
			filters["batch"] = batch_id

	if date_from and date_to:
		filters["recording_date"] = ["between", [date_from, date_to]]
	elif date_from:
		filters["recording_date"] = [">=", date_from]
	elif date_to:
		filters["recording_date"] = ["<=", date_to]

	if duration == "short":
		filters["duration_minutes"] = ["<", 30]
	elif duration == "medium":
		filters["duration_minutes"] = ["between", [30, 60]]
	elif duration == "long":
		filters["duration_minutes"] = [">", 60]

	or_filters = None
	if search and len(search.strip()) >= 2:
		term = f"%{search.strip()}%"
		or_filters = [
			["title", "like", term],
			["batch", "in", frappe.get_all("LMS Batch", filters={"title": ["like", term]}, pluck="name")],
		]

	return filters, or_filters
