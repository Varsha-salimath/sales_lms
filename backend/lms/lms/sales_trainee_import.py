# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

from __future__ import annotations

import csv
import io
import json

import frappe
from frappe import _
from frappe.utils import getdate

MANDATORY_FIELDS = ("trainee_name", "personal_email", "date_of_joining")

HEADER_ALIASES = {
	"trainee name": "trainee_name",
	"trainee_name": "trainee_name",
	"personal email": "personal_email",
	"personal_email": "personal_email",
	"email": "personal_email",
	"phone": "phone",
	"location": "location",
	"date of joining": "date_of_joining",
	"date_of_joining": "date_of_joining",
	"salary": "salary",
	"cohort": "cohort",
	"ta spoc": "ta_spoc",
	"ta_spoc": "ta_spoc",
}

TEMPLATE_HEADERS = [
	"Trainee Name",
	"Personal Email",
	"Phone",
	"Location",
	"Date of Joining",
	"Salary",
	"Cohort",
	"TA SPOC",
]


def _row_key(personal_email):
	return (personal_email or "").strip().lower()


def _normalize_header(cell: str) -> str:
	return (cell or "").strip().lower()


def _ensure_import_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to import trainees."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Sales Training Team"}):
		frappe.throw(_("You are not permitted to import trainees."), frappe.PermissionError)


def _reject_non_csv(file_content: str):
	raw = file_content or ""
	if len(raw) >= 2 and raw[0:2] == "PK":
		frappe.throw(
			_(
				"This file looks like Excel (.xlsx). Save as CSV: File → Download → Comma Separated Values (.csv), then upload again."
			),
			title=_("Use CSV format"),
		)
	if not raw.lstrip("﻿").strip():
		frappe.throw(_("The file is empty."))


def _parse_rows_from_csv(file_content: str) -> list[dict]:
	"""CSV -> row dicts, same field shape _validate_rows already expects."""
	_reject_non_csv(file_content)
	sample = (file_content or "").lstrip("﻿")
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

	required = {"trainee_name", "personal_email", "date_of_joining"}
	if not required.issubset(field_indexes.keys()):
		frappe.throw(
			_("CSV must include at least: Trainee Name, Personal Email, Date of Joining.")
		)

	parsed = []
	for line_no, raw in enumerate(raw_rows[1:], start=2):
		if not any(str(cell).strip() for cell in raw):
			continue
		item: dict = {"row": line_no}
		for field, index in field_indexes.items():
			value = raw[index].strip() if index < len(raw) and raw[index] is not None else ""
			item[field] = value or None
		parsed.append(item)
	return parsed


def _validate_rows(rows: list[dict]) -> dict:
	"""Mandatory-field + dedupe validation, extended with per-row status
	(will_create / will_update) and the errors/warnings/preview shape the
	Batches bulk-enroll modal already uses (batch_enrollment_bulk.py)."""
	errors = []
	warnings = []
	preview = []
	seen_keys: dict[str, int] = {}

	for row in rows:
		line_no = row.get("row", 0)
		row_errors = []

		for field in MANDATORY_FIELDS:
			value = row.get(field)
			if not (value.strip() if isinstance(value, str) else value):
				row_errors.append(_("Missing mandatory field '{0}'").format(field))

		key = _row_key(row.get("personal_email"))
		if key and key in seen_keys:
			row_errors.append(
				_("Duplicate personal_email '{0}' within this upload (also row {1}).").format(
					key, seen_keys[key]
				)
			)
		if key:
			seen_keys[key] = line_no

		if row.get("date_of_joining"):
			try:
				getdate(row["date_of_joining"])
			except Exception:
				row_errors.append(_("Invalid Date of Joining."))

		if row_errors:
			errors.append({"row": line_no, "email": key, "messages": row_errors})
			continue

		status = "will_update" if frappe.db.exists("Sales Trainee", {"personal_email": key}) else "will_create"
		preview.append(
			{
				"row": line_no,
				"email": key,
				"employee_name": row.get("trainee_name"),
				"status": status,
			}
		)

	return {
		"errors": errors,
		"warnings": warnings,
		"preview": preview,
		"valid_count": len(preview),
		"total_rows": len(rows),
	}


def _upsert_row(row: dict) -> str:
	"""Returns 'created' or 'updated'."""
	key = _row_key(row.get("personal_email"))
	existing = frappe.db.get_value("Sales Trainee", {"personal_email": key}, "name")
	if existing:
		doc = frappe.get_doc("Sales Trainee", existing)
		outcome = "updated"
	else:
		doc = frappe.new_doc("Sales Trainee")
		outcome = "created"
	doc.trainee_name = row.get("trainee_name")
	doc.personal_email = key
	doc.phone = row.get("phone")
	doc.location = row.get("location")
	doc.date_of_joining = getdate(row.get("date_of_joining"))
	doc.salary = row.get("salary")
	doc.cohort = row.get("cohort")
	doc.ta_spoc = row.get("ta_spoc")
	doc.save(ignore_permissions=True)
	return outcome


@frappe.whitelist()
def get_sales_trainee_import_template_csv():
	"""Downloadable header row for the onboarding upload flow, same shape as
	batch_enrollment_bulk.get_batch_upload_template_csv."""
	_ensure_import_access()
	buf = io.StringIO()
	writer = csv.writer(buf)
	writer.writerow(TEMPLATE_HEADERS)
	return buf.getvalue()


@frappe.whitelist()
def preview_sales_trainee_import(file_content, options=None):
	_ensure_import_access()
	rows = _parse_rows_from_csv(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the file."))
	return _validate_rows(rows)


@frappe.whitelist(methods=["POST"])
def commit_sales_trainee_import(file_content, options=None):
	_ensure_import_access()
	rows = _parse_rows_from_csv(file_content or "")
	if not rows:
		frappe.throw(_("No data rows found in the file."))
	validation = _validate_rows(rows)
	if validation["errors"]:
		frappe.throw(_("Fix errors before importing."))

	by_row = {row["row"]: row for row in rows}
	created, updated = 0, 0
	failed = []
	for item in validation["preview"]:
		row = by_row[item["row"]]
		try:
			outcome = _upsert_row(row)
			if outcome == "created":
				created += 1
			else:
				updated += 1
			frappe.db.commit()
		except Exception as e:  # noqa: BLE001 - one bad row must not sink the batch
			frappe.db.rollback()
			failed.append({"row": item["row"], "email": item["email"], "message": str(e)})

	return {"created": created, "updated": updated, "failed": failed, "warnings": validation.get("warnings") or []}


@frappe.whitelist(methods=["POST"])
def import_sales_trainees(rows, dry_run=True):
	"""Legacy single-shot API kept for direct row-dict callers (tests, scripts).
	New CSV-upload UI uses preview_sales_trainee_import / commit_sales_trainee_import above."""
	_ensure_import_access()
	if isinstance(rows, str):
		rows = json.loads(rows)
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")

	tagged_rows = [{**row, "row": i} for i, row in enumerate(rows, start=1)]
	validation = _validate_rows(tagged_rows)
	if validation["errors"]:
		messages = [f"Row {e['row']}: {m}" for e in validation["errors"] for m in e["messages"]]
		return {"ok": False, "errors": messages, "created": 0, "updated": 0}

	if dry_run:
		return {"ok": True, "errors": [], "created": 0, "updated": 0}

	by_row = {row["row"]: row for row in tagged_rows}
	created, updated = 0, 0
	row_errors = []
	for item in validation["preview"]:
		row = by_row[item["row"]]
		try:
			outcome = _upsert_row(row)
			if outcome == "created":
				created += 1
			else:
				updated += 1
		except Exception as e:  # noqa: BLE001 - one bad row must not sink the batch
			row_errors.append(f"Row {item['row']}: {e}")
	frappe.db.commit()
	if row_errors:
		return {"ok": False, "errors": row_errors, "created": created, "updated": updated}
	return {"ok": True, "errors": [], "created": created, "updated": updated}
