"""Whitelisted APIs for the LMS Recording Library."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from lms.lms.library import (
	build_recording_filters,
	can_manual_sync,
	format_recording_row,
	get_accessible_batches_for_user,
	get_user_google_calendars,
	mark_manual_sync,
	sync_recordings_for_user,
)
from lms.lms.google_drive import get_linked_email
from lms.lms.library_assignments import (
	get_assignment_counts,
	get_recording_assignments,
	is_library_staff,
	set_recording_assignments,
)


def _ensure_library_staff_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view the library."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator", "LMS Student"}):
		frappe.throw(_("You are not permitted to view the library."), frappe.PermissionError)


def _ensure_library_sync_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to sync recordings."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"Moderator", "Course Creator", "Batch Evaluator"}):
		frappe.throw(_("You are not permitted to sync recordings."), frappe.PermissionError)


@frappe.whitelist()
def get_recordings(
	batch_id: str | None = None,
	search: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	duration: str | None = None,
	sort_order: str = "desc",
	page: int = 1,
	page_size: int = 20,
):
	_ensure_library_staff_access()
	page = max(1, cint(page))
	page_size = min(100, max(1, cint(page_size)))
	start = (page - 1) * page_size

	filters, or_filters = build_recording_filters(
		frappe.session.user,
		batch_id=batch_id,
		search=search,
		date_from=date_from,
		date_to=date_to,
		duration=duration,
	)

	order = "recording_date desc, recording_time desc, creation desc"
	if sort_order == "asc":
		order = "recording_date asc, recording_time asc, creation asc"

	rows = frappe.get_all(
		"LMS Recording",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"batch",
			"gmail_account",
			"title",
			"recording_date",
			"recording_time",
			"duration_minutes",
			"file_size_mb",
			"session_number",
			"watch_url",
			"thumbnail_url",
			"synced_at",
			"is_archived",
			"is_unavailable",
		],
		order_by=order,
		limit_start=start,
		limit_page_length=page_size,
	)

	if or_filters:
		total = len(
			frappe.get_all(
				"LMS Recording",
				filters=filters,
				or_filters=or_filters,
				pluck="name",
			)
		)
	else:
		total = frappe.db.count("LMS Recording", filters=filters)

	formatted = [format_recording_row(frappe._dict(row)) for row in rows]
	if is_library_staff():
		counts = get_assignment_counts([row["name"] for row in formatted])
		for row in formatted:
			row["assigned_count"] = counts.get(row["name"], 0)

	return {
		"recordings": formatted,
		"total": total,
		"page": page,
		"page_size": page_size,
	}


@frappe.whitelist()
def sync_recordings(batch_id: str | None = None):
	_ensure_library_sync_access()
	allowed, remaining = can_manual_sync()
	if not allowed:
		frappe.throw(
			_("Please wait {0} seconds before syncing again.").format(remaining),
			frappe.ValidationError,
		)

	result = sync_recordings_for_user(batch_name=batch_id)
	frappe.db.commit()
	mark_manual_sync()
	return result


@frappe.whitelist()
def get_batch_filter_options():
	_ensure_library_staff_access()
	return get_accessible_batches_for_user(frappe.session.user)


@frappe.whitelist()
def get_library_stats():
	_ensure_library_staff_access()
	filters, _ = build_recording_filters(frappe.session.user)
	total = frappe.db.count("LMS Recording", filters=filters)

	calendars = get_user_google_calendars()
	linked_email = None
	if calendars:
		linked_email = get_linked_email(calendars[0].google_calendar)

	last_synced = frappe.cache.get_value(f"lms_library_last_sync:{frappe.session.user}")
	can_sync, cooldown_remaining = can_manual_sync()

	staff = is_library_staff()
	return {
		"total_recordings": total,
		"linked_email": linked_email,
		"last_synced": last_synced,
		"has_linked_account": bool(calendars),
		"is_staff": staff,
		"can_sync": can_sync and staff,
		"sync_cooldown_seconds": cooldown_remaining,
	}


@frappe.whitelist()
def search_batch_students(txt: str = "", batch: str = "", page_length: int = 20):
	"""Return enabled batch enrollees in search_link format."""
	_ensure_library_sync_access()
	if not batch or not frappe.db.exists("LMS Batch", batch):
		return []

	txt = (txt or "").strip().lower()
	page_length = min(max(cint(page_length) or 20, 1), 100)

	enrollments = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"batch": batch},
		fields=["member", "member_name"],
		order_by="member_name asc",
	)

	results = []
	for row in enrollments:
		member = row.member
		if member in ("Administrator", "Guest"):
			continue

		user = frappe.db.get_value("User", member, ["full_name", "enabled"], as_dict=True)
		if not user or not user.enabled:
			continue

		full_name = user.full_name or row.member_name or member
		if txt and txt not in f"{full_name} {member}".lower():
			continue

		results.append(
			{
				"value": member,
				"description": full_name,
				"label": full_name,
			}
		)
		if len(results) >= page_length:
			break

	return results


@frappe.whitelist()
def get_recording_assignment_details(recording: str):
	_ensure_library_sync_access()
	return get_recording_assignments(recording)


@frappe.whitelist()
def assign_recording_students(recording: str, members: str | list):
	import json

	if isinstance(members, str):
		members = json.loads(members)
	if not isinstance(members, list):
		frappe.throw(_("Members must be a list."))
	return set_recording_assignments(recording, members)
