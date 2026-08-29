"""Extend Google Calendar OAuth scopes for the recording library."""

import frappe

DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
LIBRARY_SCOPES = f"{CALENDAR_SCOPE} {DRIVE_READONLY_SCOPE}"


def patch_google_calendar_scopes():
	if getattr(frappe.flags, "lms_google_calendar_scopes_patched", False):
		return

	import frappe.integrations.doctype.google_calendar.google_calendar as google_calendar

	google_calendar.SCOPES = LIBRARY_SCOPES
	frappe.flags.lms_google_calendar_scopes_patched = True
