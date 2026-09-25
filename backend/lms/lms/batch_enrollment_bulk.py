# Copyright (c) 2026, Varsity Education and contributors
"""Bulk enroll learners into a batch from the Batch Upload Template CSV."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.utils import getdate, get_url

from lms.lms import access, content_scope
from lms.lms import team_access
from lms.lms.utils import get_lms_route

HEADER_ALIASES = {
	"batch start": "batch_start",
	"batch_start": "batch_start",
	"employee name": "employee_name",
	"employee_name": "employee_name",
	"email id": "email",
	"email": "email",
	"locations": "location",
	"location": "location",
	"training manager": "training_manager",
	"training_manager": "training_manager",
}

TEMPLATE_HEADERS = ["Batch Start", "Employee Name", "Email ID", "Locations", "Training Manager"]


def _normalize_header(cell: str) -> str:
	return (cell or "").strip().lower()


def _split_name(full_name: str) -> tuple[str, str]:
	parts = (full_name or "").strip().split(None, 1)
	if not parts:
		return "", ""
	if len(parts) == 1:
		return parts[0], ""
	return parts[0], parts[1]


def _ensure_bulk_enroll(batch: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if not roles & {"Moderator", "Batch Evaluator", "System Manager"}:
		frappe.throw(
			_("You must be a Moderator or Batch Evaluator to bulk enroll learners."),
			frappe.PermissionError,
		)
	if not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found."))
	if not content_scope.can_access("LMS Batch", batch):
		frappe.throw(_("This batch belongs to another team."), frappe.PermissionError)


def _can_create_accounts() -> bool:
	if access.is_admin():
		return True
	return frappe.db.get_value("LMS Member", frappe.session.user, "access_role") == "Admin"


def _resolve_departments(location: str | None, batch: str) -> list[str]:
	loc = (location or "").strip()
	if loc and frappe.db.exists("DocType", "LMS Department"):
		names = frappe.get_all("LMS Department", filters={"is_active": 1}, pluck="name")
		for name in names:
			if name.lower() == loc.lower():
				return [name]
		for name in names:
			if loc.lower() in name.lower():
				return [name]
	teams = content_scope.content_teams("LMS Batch", batch)
	if teams:
		return [teams[0]]
	my = team_access._my_teams()
	if my:
		return [sorted(my)[0]]
	if my is None and frappe.db.exists("LMS Department", content_scope.DEFAULT_CRT_TEAM):
		return [content_scope.DEFAULT_CRT_TEAM]
	return []


def _reject_non_csv(file_content: str):
	raw = file_content or ""
	# Excel .xlsx is a zip archive and starts with "PK"
	if len(raw) >= 2 and raw[0:2] == "PK":
		frappe.throw(
			_(
				"This file looks like Excel (.xlsx). Save as CSV: File → Download → Comma Separated Values (.csv), then upload again."
			),
			title=_("Use CSV format"),
		)
	if not raw.lstrip("\ufeff").strip():
		frappe.throw(_("The file is empty."))


def _parse_rows(file_content: str) -> list[dict]:
	_reject_non_csv(file_content)
	sample = (file_content or "").lstrip("\ufeff")
	reader = csv.reader(io.StringIO(sample))
	raw_rows = [row for row in reader]
	if not raw_rows:
		return []

	header = [_normalize_header(cell) for cell in raw_rows[0]]
	field_indexes: dict[str, int] = {}
	for idx, label in enumerate(header):
		field = HEADER_ALIASES.get(label)
		if field:
			field_indexes[field] = idx

	required = {"email", "employee_name"}
	if not required.issubset(field_indexes.keys()):
		frappe.throw(
			_(
				"CSV must include at least: Batch Start, Employee Name, Email ID, Locations, Training Manager."
			)
		)

	parsed = []
	for line_no, raw in enumerate(raw_rows[1:], start=2):
		if not any(str(cell).strip() for cell in raw):
			continue
		item: dict = {"row": line_no}
		for field, index in field_indexes.items():
			value = raw[index].strip() if index < len(raw) and raw[index] is not None else ""
			item[field] = value or None
		email = (item.get("email") or "").strip().lower()
		if not email:
			continue
		item["email"] = email
		parsed.append(item)
	return parsed


def _batch_start_matches(batch: str, row_start) -> bool:
	if not row_start:
		return True
	batch_start = frappe.db.get_value("LMS Batch", batch, "start_date")
	if not batch_start:
		return True
	try:
		return getdate(row_start) == getdate(batch_start)
	except Exception:
		return False


def _member_for_email(email: str) -> str | None:
	"""Resolve CSV email to User.name (Link target for LMS Batch Enrollment.member)."""
	email = (email or "").strip().lower()
	if not email:
		return None
	if frappe.db.exists("User", email):
		return email
	names = frappe.get_all("User", filters={"email": email}, pluck="name", limit=1)
	return names[0] if names else None


def _is_already_enrolled(batch: str, email: str) -> bool:
	member = _member_for_email(email)
	if not member:
		return False
	return bool(frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": member}))


def _validate_rows(batch: str, rows: list[dict], assign_training_manager: bool = False) -> dict:
	errors = []
	warnings = []
	preview = []
	seen_emails: dict[str, int] = {}

	batch_start = frappe.db.get_value("LMS Batch", batch, "start_date")
	seat_count = frappe.db.get_value("LMS Batch", batch, "seat_count") or 0
	enrolled = frappe.db.count("LMS Batch Enrollment", {"batch": batch})
	paid_batch = frappe.db.get_value("LMS Batch", batch, "paid_batch")

	for row in rows:
		line_no = row["row"]
		email = row["email"]
		row_errors = []

		if email in seen_emails:
			warnings.append(
				_("Row {0}: duplicate email {1} (also on row {2}).").format(
					line_no, email, seen_emails[email]
				)
			)
		seen_emails[email] = line_no

		if not frappe.utils.validate_email_address(email):
			row_errors.append(_("Invalid email."))

		already_enrolled = _is_already_enrolled(batch, email)
		if already_enrolled:
			warnings.append(
				_("Row {0}: {1} is already enrolled in this batch — will be skipped.").format(line_no, email)
			)
			if not row_errors:
				name = (row.get("employee_name") or "").strip() or frappe.db.get_value(
					"User", _member_for_email(email), "full_name"
				)
				first, last = _split_name(name or email)
				preview.append(
					{
						"row": line_no,
						"email": email,
						"employee_name": name or email,
						"first_name": first,
						"last_name": last,
						"location": row.get("location"),
						"training_manager": (row.get("training_manager") or "").strip().lower() or None,
						"departments": _resolve_departments(row.get("location"), batch) or [],
						"status": "already_enrolled",
					}
				)
			else:
				errors.append({"row": line_no, "email": email, "messages": row_errors})
			continue

		name = (row.get("employee_name") or "").strip()
		if not name:
			row_errors.append(_("Employee Name is required."))

		tm = (row.get("training_manager") or "").strip().lower()
		if assign_training_manager and tm and not team_access.resolve_user_email(tm):
			row_errors.append(
				_(
					"Training Manager {0} is not in the LMS. Add them under Team & access (or invite the user), then upload again."
				).format(tm)
			)
		elif tm and not team_access.resolve_user_email(tm):
			warnings.append(
				_(
					"Row {0}: Training Manager {1} is not an LMS user — reporting line will be skipped."
				).format(line_no, tm)
			)
		elif assign_training_manager and not tm:
			warnings.append(_("Row {0}: no Training Manager in CSV — reporting line will be skipped.").format(line_no))

		if row.get("batch_start") and batch_start and not _batch_start_matches(batch, row.get("batch_start")):
			warnings.append(
				_(
					"Row {0}: Batch Start {1} differs from this batch ({2}). Enrollment still uses the batch you opened."
				).format(line_no, row.get("batch_start"), batch_start)
			)

		departments = _resolve_departments(row.get("location"), batch)
		if not departments:
			row_errors.append(_("Could not map Locations to a team. Set batch teams or fix Locations column."))

		user_exists = bool(_member_for_email(email))

		if not user_exists and not _can_create_accounts():
			row_errors.append(
				_("User does not exist. Only Team admins / Moderators can create new accounts.")
			)

		if paid_batch:
			row_errors.append(_("This is a paid batch — bulk enroll is not supported here."))

		status = "ready"
		if not user_exists:
			status = "will_create"
		else:
			status = "will_enroll"

		if row_errors:
			errors.append({"row": line_no, "email": email, "messages": row_errors})
		else:
			first, last = _split_name(name)
			preview.append(
				{
					"row": line_no,
					"email": email,
					"employee_name": name,
					"first_name": first,
					"last_name": last,
					"location": row.get("location"),
					"training_manager": tm or None,
					"departments": departments,
					"status": status,
				}
			)

	will_add = sum(1 for p in preview if p["status"] in ("will_create", "will_enroll"))
	if seat_count and enrolled + will_add > int(seat_count):
		warnings.append(
			_("Batch seat count is {0}; {1} enrolled + {2} new would exceed capacity.").format(
				seat_count, enrolled, will_add
			)
		)

	return {
		"errors": errors,
		"warnings": warnings,
		"preview": preview,
		"valid_count": len([p for p in preview if p["status"] != "already_enrolled"]),
		"importable_count": len(preview),
		"total_rows": len(rows),
		"skip_count": len([p for p in preview if p["status"] == "already_enrolled"]),
	}


def _assign_member_teams(email: str, departments: list[str], access_role: str = "User"):
	if not departments:
		return
	primary = departments[0]
	doc = (
		frappe.get_doc("LMS Member", email)
		if frappe.db.exists("LMS Member", email)
		else frappe.new_doc("LMS Member")
	)
	doc.user = email
	doc.full_name = frappe.db.get_value("User", email, "full_name")
	# Enrolling someone in a batch must never change what they can do elsewhere. Only a brand-new
	# member gets the default role; an existing Admin or Manager in the CSV stays exactly as they are.
	if doc.is_new() or not doc.access_role:
		doc.access_role = access_role
	existing_primary = next((r.department for r in doc.get("departments") or [] if r.is_primary), None)
	if existing_primary in departments:
		primary = existing_primary
	designations = {r.department: r.designation for r in doc.get("departments") or []}
	doc.set("departments", [])
	for d in departments:
		doc.append(
			"departments",
			{"department": d, "designation": designations.get(d), "is_primary": int(d == primary)},
		)
	doc.save(ignore_permissions=True)
	access.clear_cache()


def _assign_training_manager(member_email: str, manager_email: str | None) -> bool:
	if not manager_email:
		return False
	return team_access.set_training_manager_line(member_email, manager_email)


def _normalized_manager_email(manager_email: str | None) -> str:
	if not manager_email:
		return ""
	user = team_access.resolve_user_email(manager_email) or manager_email.strip()
	return (frappe.db.get_value("User", user, "email") or user or "").strip().lower()


def _training_manager_line_matches(member_email: str, manager_email: str | None) -> bool:
	if not manager_email:
		return False
	target = _normalized_manager_email(manager_email)
	current = team_access.get_active_training_manager(member_email) or {}
	cur = (current.get("email") or "").strip().lower()
	if not cur and current.get("user"):
		cur = (
			frappe.db.get_value("User", current.get("user"), "email") or current.get("user") or ""
		).strip().lower()
	return bool(target and cur == target)


def _training_manager_assignment_changed(member_email: str, manager_email: str | None) -> bool:
	if not manager_email:
		return False
	target = _normalized_manager_email(manager_email)
	current = team_access.get_active_training_manager(member_email) or {}
	cur = (current.get("email") or "").strip().lower()
	if not cur and current.get("user"):
		cur = (
			frappe.db.get_value("User", current.get("user"), "email") or current.get("user") or ""
		).strip().lower()
	return cur != target


def _manager_user_for_email(manager_email: str | None) -> str | None:
	if not manager_email:
		return None
	manager_email = manager_email.strip().lower()
	user = frappe.db.get_value("User", {"email": manager_email}, "name")
	if user:
		return user
	if frappe.db.exists("User", manager_email):
		return manager_email
	return None


def _notify_training_managers_bulk(batch: str, assignments: list[dict]) -> None:
	"""Alert each Training Manager about learners assigned to them in this import."""
	if not assignments:
		return
	batch_title = frappe.db.get_value("LMS Batch", batch, "title") or batch
	link = get_lms_route(f"batches/{batch}#dashboard")
	by_manager: dict[str, list[dict]] = defaultdict(list)
	for row in assignments:
		mgr = row.get("manager_user")
		if mgr:
			by_manager[mgr].append(row)

	for mgr, items in by_manager.items():
		labels = []
		for it in items[:20]:
			labels.append(it.get("learner_label") or it.get("learner_email") or "")
		listing = ", ".join([x for x in labels if x])
		if len(items) > 20:
			listing = _("{0} and {1} more").format(listing, len(items) - 20)
		count = len(items)
		subject = _("{0} learner(s) assigned to you in {1}").format(count, batch_title)
		body = _("You are the Training Manager for the following learner(s) in batch {0}: {1}").format(
			batch_title, listing
		)
		notification = frappe._dict(
			{
				"subject": subject,
				"email_content": body,
				"document_type": "LMS Batch",
				"document_name": batch,
				"from_user": frappe.session.user,
				"type": "Alert",
				"link": link,
			}
		)
		make_notification_logs(notification, [mgr])
		frappe.publish_realtime("publish_lms_notifications", user=mgr, after_commit=True)


def _batch_course_titles(batch: str) -> list[str]:
	rows = frappe.get_all("Batch Course", filters={"parent": batch}, fields=["title", "course"], order_by="idx asc")
	titles = []
	for row in rows:
		label = row.title or frappe.db.get_value("LMS Course", row.course, "title") or row.course
		if label:
			titles.append(label)
	return titles


def _sync_ojt_learner_row(
	email: str,
	employee_name: str | None,
	location: str | None,
	training_manager: str | None,
	batch: str,
):
	from lms.lms.ojt_certification import DOCTYPE, make_row_key

	if not frappe.db.exists("DocType", DOCTYPE):
		return
	member = _member_for_email(email)
	batch_start = frappe.db.get_value("LMS Batch", batch, "start_date")
	if not batch_start:
		return
	email = email.strip().lower()
	tm = (training_manager or "").strip().lower() or None
	if tm and not team_access.resolve_user_email(tm):
		tm = None
	key = make_row_key(email, batch_start)
	existing = frappe.db.get_value(DOCTYPE, {"row_key": key}, "name")
	doc = frappe.get_doc(DOCTYPE, existing) if existing else frappe.new_doc(DOCTYPE)
	doc.email = email
	if member:
		doc.learner = member
	if employee_name:
		doc.employee_name = employee_name
	elif member and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("User", member, "full_name")
	if location:
		doc.location = location.strip()
	doc.batch_start = getdate(batch_start)
	if tm:
		doc.training_manager = tm
	doc.flags.from_bulk_enroll = True
	if existing:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)


def _send_bulk_enrollment_email(member: str, batch: str, *, is_new_account: bool):
	"""One enrollment email per new batch membership (bulk path skips default welcome + confirmation)."""
	outgoing = frappe.get_cached_value(
		"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
	)
	if not (outgoing or frappe.conf.get("mail_login")):
		return
	batch_row = frappe.db.get_value(
		"LMS Batch",
		batch,
		["title", "name", "start_date", "start_time", "medium"],
		as_dict=True,
	)
	if not batch_row:
		return
	student_name = frappe.db.get_value("User", member, "full_name") or member
	tm = team_access.get_active_training_manager(member)
	subject = _("You are enrolled in {0} — Infinity Learn LMS").format(batch_row.title)
	args = {
		"student_name": student_name,
		"batch_title": batch_row.title,
		"start_date": batch_row.start_date,
		"start_time": batch_row.start_time,
		"medium": batch_row.medium,
		"courses": _batch_course_titles(batch),
		"training_manager_name": tm.get("full_name") if tm else None,
		"training_manager_email": tm.get("email") if tm else None,
		"batch_url": get_url(get_lms_route(f"batches/{batch_row.name}")),
		"login_url": get_url("/login"),
		"is_new_account": is_new_account,
	}
	frappe.sendmail(
		recipients=member,
		subject=subject,
		template="bulk_batch_enrollment",
		args=args,
		header=[batch_row.title, "green"],
		retry=3,
	)


def _create_learner(email: str, first_name: str, last_name: str, departments: list[str], send_welcome: bool):
	email = email.strip().lower()
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name or "",
			"user_type": "Website User",
			"send_welcome_email": 1 if send_welcome else 0,
			"roles": [{"role": "LMS Student"}] if frappe.db.exists("Role", "LMS Student") else [],
		}
	)
	user.insert(ignore_permissions=True)
	_assign_member_teams(email, departments)
	return True


def _ensure_member_on_teams(email: str, departments: list[str]):
	if not departments:
		return
	current = []
	if frappe.db.exists("LMS Member", email):
		current = frappe.get_all(
			"LMS Member Department",
			filters={"parenttype": "LMS Member", "parent": email},
			pluck="department",
		)
	merged = list(dict.fromkeys([*current, *departments]))
	_assign_member_teams(email, merged)


def _enroll_member(batch: str, member_email: str) -> bool:
	member = _member_for_email(member_email) or member_email
	if _is_already_enrolled(batch, member_email):
		return False
	frappe.flags.skip_batch_confirmation_email = True
	try:
		doc = frappe.get_doc({"doctype": "LMS Batch Enrollment", "member": member, "batch": batch})
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError as exc:
		if exc.args and "already enrolled" in str(exc.args[0]).lower():
			return False
		raise
	finally:
		frappe.flags.skip_batch_confirmation_email = False
	return True


@frappe.whitelist()
def get_batch_upload_template_csv(batch: str | None = None):
	"""Downloadable header row (and sample line) for the bulk enroll dialog."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	roles = set(frappe.get_roles())
	if not roles & {"Moderator", "Batch Evaluator", "System Manager"}:
		frappe.throw(_("You must be a Moderator or Batch Evaluator."), frappe.PermissionError)
	buf = io.StringIO()
	writer = csv.writer(buf)
	writer.writerow(TEMPLATE_HEADERS)
	if batch and frappe.db.exists("LMS Batch", batch):
		start = frappe.db.get_value("LMS Batch", batch, "start_date")
		start_label = frappe.utils.formatdate(start) if start else ""
		writer.writerow([start_label, "", "", "", ""])
	return buf.getvalue()


@frappe.whitelist()
def preview_batch_enrollment_upload(batch: str, file_content: str, options: str | None = None):
	_ensure_bulk_enroll(batch)
	opts = json.loads(options or "{}")
	assign_tm = bool(opts.get("assign_training_manager", True))
	rows = _parse_rows(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the file."))
	result = _validate_rows(batch, rows, assign_training_manager=assign_tm)
	result["batch"] = batch
	return result


@frappe.whitelist(methods=["POST"])
def commit_batch_enrollment_upload(batch: str, file_content: str, options: str | None = None):
	_ensure_bulk_enroll(batch)
	opts = json.loads(options or "{}")
	send_welcome = bool(opts.get("send_welcome", True))
	assign_tm = bool(opts.get("assign_training_manager", True))

	rows = _parse_rows(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the file."))
	validation = _validate_rows(batch, rows, assign_training_manager=assign_tm)
	if validation["errors"]:
		frappe.throw(_("Fix errors before importing."))

	created = 0
	enrolled = 0
	skipped = 0
	failed = []
	tm_notifications: list[dict] = []

	seen_tm_notify: set[tuple[str, str]] = set()

	def _queue_tm_notification(item: dict, manager_email: str | None) -> None:
		if not assign_tm or not manager_email:
			return
		mgr_user = _manager_user_for_email(manager_email)
		if not mgr_user:
			return
		learner_email = (item.get("email") or "").strip().lower()
		key = (mgr_user, learner_email)
		if key in seen_tm_notify:
			return
		seen_tm_notify.add(key)
		learner_label = (
			item.get("employee_name")
			or " ".join(filter(None, [item.get("first_name"), item.get("last_name")])).strip()
			or item.get("email")
		)
		tm_notifications.append(
			{
				"manager_user": mgr_user,
				"learner_email": learner_email,
				"learner_label": learner_label,
			}
		)

	for item in validation["preview"]:
		email = item["email"]
		tm = item.get("training_manager")
		if item["status"] == "already_enrolled":
			skipped += 1
			try:
				if item.get("departments"):
					_ensure_member_on_teams(email, item["departments"])
				if assign_tm and tm:
					notify_tm = _training_manager_assignment_changed(email, tm)
					_assign_training_manager(email, tm)
					if notify_tm and _training_manager_line_matches(email, tm):
						_queue_tm_notification(item, tm)
				_sync_ojt_learner_row(
					email,
					item.get("employee_name"),
					item.get("location"),
					tm if assign_tm else None,
					batch,
				)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
			continue
		try:
			is_new = not _member_for_email(email)
			if is_new:
				# Bulk sends one combined enrollment email; skip Frappe default welcome.
				_create_learner(
					email,
					item["first_name"],
					item["last_name"],
					item["departments"],
					send_welcome=False,
				)
				created += 1
			else:
				_ensure_member_on_teams(email, item["departments"])

			notify_tm = bool(assign_tm and tm and _training_manager_assignment_changed(email, tm))
			if assign_tm and tm:
				_assign_training_manager(email, tm)

			did_enroll = _enroll_member(batch, email)
			if did_enroll:
				enrolled += 1
				member_id = _member_for_email(email) or email
				_sync_ojt_learner_row(
					email,
					item.get("employee_name"),
					item.get("location"),
					tm if assign_tm else None,
					batch,
				)
				# One email per new batch membership (re-bulk skips already_enrolled). New accounts only
				# when "Send welcome" is checked; existing users always get the batch notice once.
				if not is_new or send_welcome:
					_send_bulk_enrollment_email(
						member_id,
						batch,
						is_new_account=bool(is_new and send_welcome),
					)
				if assign_tm and tm and (did_enroll or notify_tm) and _training_manager_line_matches(email, tm):
					_queue_tm_notification(item, tm)
			frappe.db.commit()
		except Exception as exc:
			frappe.db.rollback()
			msg = getattr(exc, "message", None) or str(exc)
			if isinstance(exc, frappe.ValidationError) and exc.args:
				msg = exc.args[0]
			if "already enrolled" in str(msg).lower():
				skipped += 1
				continue
			failed.append({"row": item["row"], "email": email, "message": msg})
			continue

	_notify_training_managers_bulk(batch, tm_notifications)
	return {
		"created": created,
		"enrolled": enrolled,
		"skipped": skipped,
		"failed": failed,
		"warnings": validation.get("warnings") or [],
	}
