# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark


def sync_from_live_class_participant(doc, event=None):
	"""Bridge the existing Zoom-based live-class attendance sync into the trainee
	attendance ledger. Matches by personal_email since Sales Trainee has no User
	link. A pre-existing Manual row for the same day is left untouched — Zoom sync
	never clobbers a staff correction."""
	email = (doc.member or "").strip().lower()
	if not email:
		return
	trainee = frappe.db.get_value("Sales Trainee", {"personal_email": email}, "name")
	if not trainee:
		return
	attendance_date = getdate(doc.joined_at)
	existing = frappe.db.get_value(
		"Sales Trainee Attendance", {"trainee": trainee, "attendance_date": attendance_date}, ["name", "source"], as_dict=True
	)
	if existing and existing.source == "Manual":
		return
	mark(trainee, attendance_date, "Present", source="Zoom Sync", marked_by="Administrator")
