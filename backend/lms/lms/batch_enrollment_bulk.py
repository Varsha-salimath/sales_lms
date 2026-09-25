# Copyright (c) 2026, Varsity Education and contributors
"""Bulk enroll learners into a batch from the Batch Upload Template CSV."""

from __future__ import annotations

import csv
import io
import json

import frappe
from frappe import _
from frappe.utils import getdate

from lms.lms import access, content_scope
from lms.lms import team_access

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


def _validate_rows(batch: str, rows: list[dict]) -> dict:
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
		if tm and not frappe.db.exists("User", tm):
			warnings.append(
				_(
					"Row {0}: Training Manager {1} is not an LMS user — reporting line will be skipped (add them under Team & access or fix the email)."
				).format(line_no, tm)
			)
		elif not tm:
			warnings.append(_("Row {0}: no Training Manager — reporting line will be skipped.").format(line_no))

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


def _ensure_reporting_line(member: str, manager: str):
	if not manager or not frappe.db.exists("User", manager):
		return
	if not (access.is_admin() or frappe.db.get_value("LMS Member", frappe.session.user, "access_role") == "Admin"):
		return
	exists = frappe.db.exists(
		"LMS Reporting Line",
		{
			"member": member,
			"manager": manager,
			"line_type": "Training Manager",
			"status": "Active",
		},
	)
	if exists:
		return
	team_access.add_reporting_line(member, manager, "Training Manager")


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


def _enroll_member(batch: str, member_email: str):
	member = _member_for_email(member_email) or member_email
	if _is_already_enrolled(batch, member_email):
		return False
	doc = frappe.get_doc({"doctype": "LMS Batch Enrollment", "member": member, "batch": batch})
	try:
		doc.insert(ignore_permissions=True)
	except frappe.ValidationError as exc:
		if exc.args and "already enrolled" in str(exc.args[0]).lower():
			return False
		raise
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
def preview_batch_enrollment_upload(batch: str, file_content: str):
	_ensure_bulk_enroll(batch)
	rows = _parse_rows(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the file."))
	result = _validate_rows(batch, rows)
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
	validation = _validate_rows(batch, rows)
	if validation["errors"]:
		frappe.throw(_("Fix errors before importing."))

	created = 0
	enrolled = 0
	skipped = 0
	failed = []

	for item in validation["preview"]:
		email = item["email"]
		if item["status"] == "already_enrolled":
			skipped += 1
			try:
				if item.get("departments"):
					_ensure_member_on_teams(email, item["departments"])
				tm = item.get("training_manager")
				if assign_tm and tm and frappe.db.exists("User", tm):
					_ensure_reporting_line(email, tm)
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
			continue
		try:
			if not _member_for_email(email):
				_create_learner(
					email,
					item["first_name"],
					item["last_name"],
					item["departments"],
					send_welcome,
				)
				created += 1
			else:
				_ensure_member_on_teams(email, item["departments"])

			tm = item.get("training_manager")
			if assign_tm and tm and frappe.db.exists("User", tm):
				try:
					_ensure_reporting_line(email, tm)
				except Exception:
					pass

			if _enroll_member(batch, email):
				enrolled += 1
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
	return {
		"created": created,
		"enrolled": enrolled,
		"skipped": skipped,
		"failed": failed,
		"warnings": validation.get("warnings") or [],
	}
