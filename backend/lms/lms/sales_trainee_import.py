# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

MANDATORY_FIELDS = ("trainee_name", "personal_email", "date_of_joining")


def _row_key(personal_email):
	return (personal_email or "").strip().lower()


def _validate_rows(rows):
	errors = []
	seen_keys = set()
	for i, row in enumerate(rows, start=1):
		for field in MANDATORY_FIELDS:
			if not (row.get(field) or "").strip() if isinstance(row.get(field), str) else not row.get(field):
				errors.append(f"Row {i}: missing mandatory field '{field}'")
		key = _row_key(row.get("personal_email"))
		if key:
			if key in seen_keys:
				errors.append(f"Row {i}: duplicate personal_email '{row.get('personal_email')}' within this upload")
			seen_keys.add(key)
	return errors


@frappe.whitelist(methods=["POST"])
def import_sales_trainees(rows, dry_run=True):
	"""Bulk upsert Sales Trainee records, deduped by personal_email — same shape as
	ojt_certification.py's row-key upsert. dry_run=True validates only, never writes."""
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")
	errors = _validate_rows(rows)
	if errors:
		return {"ok": False, "errors": errors, "created": 0, "updated": 0}
	if dry_run:
		return {"ok": True, "errors": [], "created": 0, "updated": 0}

	created, updated = 0, 0
	row_errors = []
	for i, row in enumerate(rows, start=1):
		try:
			key = _row_key(row.get("personal_email"))
			existing = frappe.db.get_value("Sales Trainee", {"personal_email": key}, "name")
			if existing:
				doc = frappe.get_doc("Sales Trainee", existing)
				updated += 1
			else:
				doc = frappe.new_doc("Sales Trainee")
				created += 1
			doc.trainee_name = row.get("trainee_name")
			doc.personal_email = key
			doc.phone = row.get("phone")
			doc.location = row.get("location")
			doc.date_of_joining = getdate(row.get("date_of_joining"))
			doc.salary = row.get("salary")
			doc.cohort = row.get("cohort")
			doc.ta_spoc = row.get("ta_spoc")
			doc.save(ignore_permissions=True)
		except Exception as e:  # noqa: BLE001 - one bad row must not sink the batch
			row_errors.append(f"Row {i}: {e}")
	frappe.db.commit()
	if row_errors:
		return {"ok": False, "errors": row_errors, "created": created, "updated": updated}
	return {"ok": True, "errors": [], "created": created, "updated": updated}
