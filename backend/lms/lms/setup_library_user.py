"""One-time helper to wire Library + Google Meet for an instructor."""

import frappe
from frappe import _
from frappe.utils import add_days, nowdate


def setup_library_user(
	email: str,
	account_name: str | None = None,
	batch_name: str | None = None,
):
	"""Create evaluator, Google Calendar, and Meet settings for an instructor."""
	email = email.strip().lower()
	if not email:
		frappe.throw(_("Email is required."))

	account_name = account_name or email.split("@")[0].replace(".", "-")
	calendar_name = email

	_ensure_user(email)
	_ensure_course_evaluator(email)
	calendar_docname = _ensure_google_calendar(email, calendar_name)
	meet_name = _ensure_google_meet_settings(email, account_name, calendar_docname)

	if batch_name:
		_link_batch_to_meet(batch_name, meet_name)

	frappe.db.commit()
	return {
		"email": email,
		"google_calendar": calendar_docname,
		"google_meet_account": meet_name,
		"batch": batch_name,
		"next_steps": [
			"Configure Google Settings (Client ID + Secret) in Desk if not done.",
			f"Authorize Google Calendar: /app/google-calendar/{calendar_docname}",
			"Log in to LMS as this user (or use Library while logged in as them).",
			"Open Library and click Sync Now after OAuth is complete.",
		],
	}


def configure_google_settings(client_id: str, client_secret: str):
	"""Enable Frappe Google Settings with OAuth credentials from Google Cloud Console."""
	settings = frappe.get_single("Google Settings")
	settings.enable = 1
	settings.client_id = client_id.strip()
	settings.client_secret = client_secret.strip()
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	return {"enabled": True, "client_id": settings.client_id}


def _ensure_user(email: str, first_name: str | None = None, last_name: str | None = None):
	if frappe.db.exists("User", email):
		return frappe.get_doc("User", email)

	local = email.split("@")[0]
	parts = local.replace(".", " ").replace("_", " ").split()
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name or (parts[0].title() if parts else local),
			"last_name": last_name or (" ".join(parts[1:]).title() if len(parts) > 1 else ""),
			"send_welcome_email": 0,
		}
	)
	user.insert(ignore_permissions=True)

	for role in ("LMS Student", "Batch Evaluator", "Course Creator", "Moderator"):
		if frappe.db.exists("Role", role):
			user.add_roles(role)
	return user


def _ensure_course_evaluator(email: str):
	if frappe.db.exists("Course Evaluator", email):
		return

	frappe.get_doc({"doctype": "Course Evaluator", "evaluator": email}).insert(
		ignore_permissions=True
	)


def _ensure_google_calendar(user: str, calendar_name: str) -> str:
	existing = frappe.db.get_value("Google Calendar", {"user": user}, "name")
	if existing:
		frappe.db.set_value("Google Calendar", existing, "enable", 1)
		return existing

	cal = frappe.get_doc(
		{
			"doctype": "Google Calendar",
			"user": user,
			"calendar_name": calendar_name,
			"enable": 1,
		}
	)
	cal.flags.ignore_validate = True
	cal.insert(ignore_permissions=True)
	return cal.name


def _ensure_google_meet_settings(member: str, account_name: str, google_calendar: str) -> str:
	existing = frappe.db.get_value("LMS Google Meet Settings", {"member": member}, "name")
	if existing:
		frappe.db.set_value(
			"LMS Google Meet Settings",
			existing,
			{"google_calendar": google_calendar, "enabled": 1},
		)
		return existing

	meet = frappe.get_doc(
		{
			"doctype": "LMS Google Meet Settings",
			"account_name": account_name,
			"member": member,
			"google_calendar": google_calendar,
			"enabled": 1,
		}
	)
	meet.insert(ignore_permissions=True)
	return meet.name


def _link_batch_to_meet(batch_name: str, meet_account: str):
	if not frappe.db.exists("LMS Batch", batch_name):
		frappe.throw(_("Batch {0} not found.").format(batch_name))

	frappe.db.set_value(
		"LMS Batch",
		batch_name,
		{
			"conferencing_provider": "Google Meet",
			"google_meet_account": meet_account,
			"allow_recording_library": 1,
		},
	)


def reassign_cohort_instructor(
	instructor_email: str,
	course_name: str | None = None,
	batch_name: str | None = None,
	extra_members: list[str] | None = None,
):
	"""Point an existing course/batch at a new instructor + Google Meet account."""
	instructor_email = instructor_email.strip().lower()
	setup_library_user(instructor_email)
	meet_account = frappe.db.get_value(
		"LMS Google Meet Settings", {"member": instructor_email}, "name"
	)

	course_name = course_name or frappe.db.get_value("LMS Course", {}, "name")
	batch_name = batch_name or frappe.db.get_value("LMS Batch", {}, "name")
	if not course_name or not batch_name:
		frappe.throw(_("No course/batch found to reassign."))

	course = frappe.get_doc("LMS Course", course_name)
	course.set("instructors", [])
	course.append("instructors", {"instructor": instructor_email})
	course.save(ignore_permissions=True)

	batch = frappe.get_doc("LMS Batch", batch_name)
	batch.set("instructors", [])
	batch.append("instructors", {"instructor": instructor_email})
	for row in batch.courses:
		row.evaluator = instructor_email
	batch.google_meet_account = meet_account
	batch.conferencing_provider = "Google Meet"
	batch.allow_recording_library = 1
	batch.save(ignore_permissions=True)

	members = list(dict.fromkeys([instructor_email, *(extra_members or [])]))
	for email in members:
		_ensure_user(email)
		_ensure_batch_enrollment(email, batch.name)

	frappe.db.commit()
	return {
		"course": course.name,
		"batch": batch.name,
		"instructor": instructor_email,
		"google_meet_account": meet_account,
		"members": members,
	}


def link_demo_cohort_for_instructor(
	instructor_email: str,
	member_emails: list[str] | None = None,
	course_title: str = "Coding and Robotics",
	batch_title: str = "B28 - Grade 2 Batch B",
):
	"""Create a published course + batch and enroll the instructor and teammates."""
	instructor_email = instructor_email.strip().lower()
	member_emails = member_emails or []
	all_members = list(dict.fromkeys([instructor_email, *member_emails]))

	setup_library_user(instructor_email)
	meet_account = frappe.db.get_value(
		"LMS Google Meet Settings", {"member": instructor_email}, "name"
	)

	for email in all_members:
		_ensure_user(email)
		if email != instructor_email and "LMS Student" not in frappe.get_roles(email):
			frappe.get_doc("User", email).add_roles("LMS Student")

	course = _ensure_demo_course(course_title, instructor_email)
	batch = _ensure_demo_batch(batch_title, course.name, instructor_email, meet_account)

	for email in all_members:
		_ensure_batch_enrollment(email, batch.name)

	frappe.db.commit()
	return {
		"course": course.name,
		"course_title": course.title,
		"batch": batch.name,
		"batch_title": batch.title,
		"google_meet_account": meet_account,
		"members": all_members,
	}


def _ensure_demo_course(title: str, instructor: str):
	existing = frappe.db.get_value("LMS Course", {"title": title}, "name")
	if existing:
		return frappe.get_doc("LMS Course", existing)

	if not frappe.db.exists("LMS Category", "Business"):
		frappe.get_doc({"doctype": "LMS Category", "category": "Business"}).insert(
			ignore_permissions=True
		)

	course = frappe.get_doc(
		{
			"doctype": "LMS Course",
			"title": title,
			"short_introduction": title,
			"description": f"Demo course for {title}.",
			"tags": "Genius,Library,Demo",
			"category": "Business",
			"published": 1,
			"instructors": [{"instructor": instructor}],
		}
	)
	course.insert(ignore_permissions=True)
	return course


def _ensure_demo_batch(title: str, course: str, instructor: str, meet_account: str | None):
	existing = frappe.db.get_value("LMS Batch", {"title": title}, "name")
	if existing:
		batch = frappe.get_doc("LMS Batch", existing)
		batch.google_meet_account = meet_account
		batch.conferencing_provider = "Google Meet"
		batch.allow_recording_library = 1
		batch.save(ignore_permissions=True)
		return batch

	batch = frappe.get_doc(
		{
			"doctype": "LMS Batch",
			"title": title,
			"start_date": nowdate(),
			"end_date": add_days(nowdate(), 21),
			"start_time": "10:00:00",
			"end_time": "11:00:00",
			"timezone": "Asia/Kolkata",
			"published": 1,
			"description": f"Demo batch for Library testing ({title}).",
			"batch_details": "Batch linked for Google Meet recordings library.",
			"evaluation_end_date": add_days(nowdate(), 120),
			"conferencing_provider": "Google Meet",
			"google_meet_account": meet_account,
			"allow_recording_library": 1,
			"allow_self_enrollment": 1,
			"instructors": [{"instructor": instructor}],
			"courses": [{"course": course, "evaluator": instructor}],
		}
	)
	batch.insert(ignore_permissions=True)
	return batch


def _ensure_batch_enrollment(member: str, batch: str):
	if frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": member}):
		return

	frappe.get_doc(
		{
			"doctype": "LMS Batch Enrollment",
			"member": member,
			"batch": batch,
			"confirmation_email_sent": 1,
		}
	).insert(ignore_permissions=True)
