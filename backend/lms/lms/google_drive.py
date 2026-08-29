"""Google Drive API helpers for the LMS Recording Library."""

import frappe
import requests
from frappe import _

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def get_google_settings():
	settings = frappe.get_single("Google Settings")
	if not settings.enable:
		frappe.throw(_("Google integration is not enabled. Configure Google Settings first."))
	return settings


def get_access_token(google_calendar_name: str) -> str:
	"""Refresh and return a Google access token for the linked calendar account."""
	calendar = frappe.get_doc("Google Calendar", google_calendar_name)
	refresh_token = calendar.get_password("refresh_token")
	if not refresh_token:
		frappe.throw(
			_("Google account is not authorized. Please re-link your Google account in Settings.")
		)

	settings = get_google_settings()
	response = requests.post(
		GOOGLE_TOKEN_URL,
		data={
			"client_id": settings.client_id,
			"client_secret": settings.get_password("client_secret"),
			"refresh_token": refresh_token,
			"grant_type": "refresh_token",
		},
		timeout=30,
	)
	if response.status_code != 200:
		frappe.log_error(
			title="Google Drive token refresh failed",
			message=response.text,
		)
		frappe.throw(_("Failed to refresh Google access token. Please re-link your Google account."))

	return response.json()["access_token"]


def get_linked_email(google_calendar_name: str) -> str | None:
	cache_key = f"lms_library_gmail:{google_calendar_name}"
	cached = frappe.cache.get_value(cache_key)
	if cached:
		return cached

	try:
		access_token = get_access_token(google_calendar_name)
		response = requests.get(
			GOOGLE_USERINFO_URL,
			headers={"Authorization": f"Bearer {access_token}"},
			timeout=30,
		)
		if response.status_code == 200:
			email = response.json().get("email")
			if email:
				frappe.cache.set_value(cache_key, email, expires_in_sec=3600)
				return email
	except Exception:
		frappe.log_error(title="Failed to fetch linked Gmail for library")

	return frappe.db.get_value("Google Calendar", google_calendar_name, "calendar_name")


def list_recordings_from_drive(
	google_calendar_name: str,
	batch_code: str,
	start_date: str,
	end_date: str,
	page_token: str | None = None,
) -> dict:
	"""Query Google Drive for mp4 recordings matching a batch code and date range."""
	access_token = get_access_token(google_calendar_name)
	query = (
		f"name contains '{batch_code}' "
		f"and mimeType='video/mp4' "
		f"and createdTime >= '{start_date}T00:00:00Z' "
		f"and createdTime <= '{end_date}T23:59:59Z' "
		f"and trashed=false"
	)
	params = {
		"q": query,
		"fields": "nextPageToken,files(id,name,createdTime,webViewLink,thumbnailLink,size,videoMediaMetadata)",
		"orderBy": "createdTime desc",
		"pageSize": 100,
		"supportsAllDrives": True,
		"includeItemsFromAllDrives": True,
	}
	if page_token:
		params["pageToken"] = page_token

	response = requests.get(
		DRIVE_FILES_URL,
		headers={"Authorization": f"Bearer {access_token}"},
		params=params,
		timeout=60,
	)

	if response.status_code == 403:
		frappe.log_error(title="Google Drive API quota exceeded", message=response.text)
		frappe.throw(_("Google Drive sync is temporarily unavailable. Please try again later."))

	if response.status_code != 200:
		frappe.log_error(title="Google Drive API error", message=response.text)
		frappe.throw(_("Failed to fetch recordings from Google Drive."))

	return response.json()


def check_file_available(google_calendar_name: str, drive_file_id: str) -> bool:
	access_token = get_access_token(google_calendar_name)
	response = requests.get(
		f"{DRIVE_FILES_URL}/{drive_file_id}",
		headers={"Authorization": f"Bearer {access_token}"},
		params={"fields": "id,trashed"},
		timeout=30,
	)
	if response.status_code == 404:
		return False
	if response.status_code != 200:
		return True
	data = response.json()
	return not data.get("trashed")


