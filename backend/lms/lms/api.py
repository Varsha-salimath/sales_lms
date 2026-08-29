"""API methods for the LMS."""

import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import timedelta
from xml.dom.minidom import parseString

import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import (
	current_site_info,
	is_fc_site,
)
from frappe.translate import get_all_translations
from frappe.utils import (
	add_days,
	cint,
	cstr,
	cstr,
	date_diff,
	flt,
	format_date,
	get_datetime,
	getdate,
	now,
)
from frappe.utils.response import Response
from pypika import functions as fn

from lms.lms.course_import_export import export_course_zip, import_course_zip
from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms.lms.utils import (
	LMS_ROLES,
	can_modify_batch,
	can_modify_course,
	get_batch_details,
	get_course_details,
	get_field_meta,
	get_instructors,
	get_lessons,
	get_lessons,
	get_lms_route,
	has_course_instructor_role,
	has_evaluator_role,
	has_lms_role,
	has_moderator_role,
)


@frappe.whitelist()
def get_user_info():
	if frappe.session.user == "Guest":
		return None

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		["name", "email", "enabled", "user_image", "full_name", "user_type", "username", "bio", "headline"],
		as_dict=1,
	)
	user["roles"] = frappe.get_roles(user.name)
	user.is_instructor = "Course Creator" in user.roles
	user.is_moderator = "Moderator" in user.roles
	user.is_evaluator = "Batch Evaluator" in user.roles
	user.is_student = not user.is_instructor and not user.is_moderator and not user.is_evaluator
	user.is_fc_site = is_fc_site()
	user.is_system_manager = "System Manager" in user.roles
	user.sitename = frappe.local.site
	user.developer_mode = frappe.conf.developer_mode
	if user.is_fc_site and user.is_system_manager:
		user.site_info = current_site_info()
	return user


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")
	return get_all_translations(language)


@frappe.whitelist()
def validate_billing_access(billing_type: str, name: str):
	doctype = "LMS Batch" if billing_type == "batch" else "LMS Course"
	access, message = verify_billing_access(doctype, name, billing_type)

	address = frappe.db.get_value(
		"Address",
		{"email_id": frappe.session.user},
		[
			"name",
			"address_title as billing_name",
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
			"phone",
		],
		as_dict=1,
	)

	payment_fields = get_payment_field_meta()
	address_fields = get_field_meta(
		"Address",
		[
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
			"phone",
		],
	)
	billing_field_meta = {**payment_fields, **address_fields}

	return {
		"access": access,
		"message": message,
		"address": address,
		"billing_field_meta": billing_field_meta,
	}


@frappe.whitelist()
def get_payment_field_meta():
	return get_field_meta(
		"LMS Payment",
		[
			"member",
			"billing_name",
			"source",
			"payment_for_document_type",
			"payment_for_document",
			"currency",
			"amount",
			"amount_with_gst",
			"original_amount",
			"discount_amount",
			"coupon",
			"coupon_code",
			"address",
			"gstin",
			"pan",
			"payment_id",
			"order_id",
			"member_consent",
		],
	)


def verify_billing_access(doctype, name, billing_type):
	access = True
	message = ""

	if frappe.session.user == "Guest":
		access = False
		message = _("Please login to continue with payment.")

	if access and billing_type not in ["course", "batch", "certificate"]:
		access = False
		message = _("Module is incorrect.")

	if access and not frappe.db.exists(doctype, name):
		access = False
		message = _("Module Name is incorrect or does not exist.")

	if access and billing_type == "course":
		membership = frappe.db.exists("LMS Enrollment", {"member": frappe.session.user, "course": name})
		if membership:
			access = False
			message = _("You are already enrolled for this course.")

	elif access and billing_type == "batch":
		membership = frappe.db.exists("LMS Batch Enrollment", {"member": frappe.session.user, "batch": name})
		if membership:
			access = False
			message = _("You are already enrolled for this batch.")

		seat_count = frappe.get_cached_value("LMS Batch", name, "seat_count")
		number_of_students = frappe.db.count("LMS Batch Enrollment", {"batch": name})
		if seat_count <= number_of_students:
			access = False
			message = _("Batch is sold out.")

		start_date = frappe.get_cached_value("LMS Batch", name, "start_date")
		if start_date and date_diff(start_date, now()) < 0:
			access = False
			message = _("Batch has already started.")

	elif access and billing_type == "certificate":
		purchased_certificate = frappe.db.exists(
			"LMS Enrollment",
			{
				"course": name,
				"member": frappe.session.user,
				"purchased_certificate": 1,
			},
		)
		if purchased_certificate:
			access = False
			message = _("You have already purchased the certificate for this course.")

	return access, message


@frappe.whitelist(allow_guest=True)
def get_job_details(job: str):
	return frappe.db.get_value(
		"Job Opportunity",
		job,
		[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"company_website",
			"name",
			"creation",
			"description",
			"owner",
		],
		as_dict=1,
	)


def sanitize_job_filters(filters, or_filters):
	ALLOWED_FILTERS = ("status", "type", "work_mode", "country")
	ALLOWED_OR_FILTERS = ("job_title", "company_name", "location")

	filters = {f: v for f, v in (filters or {}).items() if f in ALLOWED_FILTERS}
	or_filters = {f: v for f, v in (or_filters or {}).items() if f in ALLOWED_OR_FILTERS}

	if filters.get("status") == "Closed" and "Moderator" not in frappe.get_roles():
		filters["owner"] = frappe.session.user

	return filters, or_filters


@frappe.whitelist(allow_guest=True)
def get_job_opportunities(
	filters: dict = None, or_filters: dict = None, start: int = 0, page_length: int = 40
):
	filters, or_filters = sanitize_job_filters(filters, or_filters)

	jobs = frappe.get_all(
		"Job Opportunity",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"name",
			"creation",
			"description",
		],
		start=start,
		page_length=page_length,
		order_by="creation desc",
	)

	for job in jobs:
		job.description = frappe.utils.strip_html_tags(job.description)
		job.applicants = frappe.db.count("LMS Job Application", {"job": job.name})
	return jobs


@frappe.whitelist(allow_guest=True)
def get_job_opportunities_count(filters: dict = None, or_filters: dict = None):
	filters, or_filters = sanitize_job_filters(filters, or_filters)
	return frappe.db.count("Job Opportunity", filters, or_filters)


@frappe.whitelist()
def get_chart_details():
	"""Site-wide enrollment/course metrics — staff analytics only (no guest)."""
	_ensure_analytics_access()
	details = frappe._dict()
	details.enrollments = frappe.db.count("LMS Enrollment")
	details.courses = frappe.db.count(
		"LMS Course",
		{
			"published": 1,
			"upcoming": 0,
		},
	)
	details.users = frappe.db.count("User", {"enabled": 1, "name": ["not in", ("Administrator", "Guest")]})
	details.completions = frappe.db.count("LMS Enrollment", {"progress": [">=", 100]})
	details.certifications = frappe.db.count("LMS Certificate", {"published": 1})
	return details


def _ensure_analytics_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}):
		frappe.throw(_("You are not permitted to view analytics."), frappe.PermissionError)


@frappe.whitelist()
def get_analytics_overview():
	"""Overview metrics for the analytics dashboard (site-wide, non-students only)."""
	_ensure_analytics_access()

	from frappe.utils import add_days, get_first_day, getdate

	today = getdate()
	month_start = get_first_day(today)
	active_since = add_days(today, -15)
	week_start = add_days(today, -7)

	total_courses = frappe.db.count("LMS Course")
	published_this_month = frappe.db.count(
		"LMS Course",
		{"published": 1, "published_on": [">=", month_start]},
	)

	total_users = frappe.db.count(
		"User",
		{
			"enabled": 1,
			"name": ["not in", ("Guest",)],
		},
	)

	student_users = frappe.get_all(
		"Has Role",
		filters={"role": "LMS Student", "parenttype": "User"},
		pluck="parent",
	)
	if student_users:
		active_learners = frappe.db.count(
			"User",
			{
				"name": ["in", student_users],
				"enabled": 1,
				"last_active": [">=", active_since],
			},
		)
	else:
		active_learners = 0

	avg_completion = frappe.db.sql(
		"SELECT AVG(progress) FROM `tabLMS Enrollment`",
	)[0][0]
	avg_completion = cint(flt(avg_completion, 0))

	total_certificates = frappe.db.count("LMS Certificate", {"published": 1})
	certificates_this_week = frappe.db.count(
		"LMS Certificate",
		{"published": 1, "issue_date": [">=", week_start]},
	)

	return {
		"total_courses": {
			"value": total_courses,
			"subtext": _("{0} published this month").format(published_this_month),
		},
		"total_users": {
			"value": total_users,
			"subtext": _("Total registered"),
		},
		"active_learners": {
			"value": active_learners,
			"subtext": _("Last 15 days"),
		},
		"avg_completion": {
			"value": avg_completion,
			"subtext": _("Across all courses"),
		},
		"certificates_issued": {
			"value": total_certificates,
			"subtext": _("+{0} this week").format(certificates_this_week),
		},
	}


def _ensure_admin_dashboard_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view the admin dashboard."), frappe.PermissionError)

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"Moderator", "System Manager"}):
		frappe.throw(_("You are not permitted to view the admin dashboard."), frappe.PermissionError)


def _month_labels(months=6):
	from frappe.utils import add_months, get_first_day

	labels = []
	cursor = get_first_day(getdate())
	for _ in range(months):
		labels.append(
			{
				"key": cursor.strftime("%Y-%m"),
				"label": cursor.strftime("%b %Y"),
				"start": cursor,
			}
		)
		cursor = add_months(cursor, -1)
	labels.reverse()
	return labels


@frappe.whitelist()
def get_admin_dashboard_data():
	"""SaaS-style admin portal metrics for Moderator / System Manager."""
	_ensure_admin_dashboard_access()

	from frappe.utils import add_months, get_first_day, now_datetime

	today = getdate()
	month_start = get_first_day(today)
	prev_month_start = get_first_day(add_months(today, -1))
	active_since = add_days(today, -30)
	week_start = add_days(today, -7)

	# Exclude seed demo course (same rule as AdminDashboard / Courses UI)
	from lms.lms.utils import is_demo_course

	demo_course_names = [
		row.name
		for row in frappe.get_all("LMS Course", fields=["name"])
		if is_demo_course(row.name)
	]
	course_filters = {"name": ["not in", demo_course_names]} if demo_course_names else {}

	total_courses = frappe.db.count("LMS Course", course_filters or None)
	published_courses = frappe.db.count(
		"LMS Course", {**course_filters, "published": 1}
	)
	draft_courses = frappe.db.count("LMS Course", {**course_filters, "published": 0})
	prev_total_courses = frappe.db.count(
		"LMS Course", {**course_filters, "creation": ["<", month_start]}
	)

	total_programs = frappe.db.count("LMS Program") if frappe.db.exists("DocType", "LMS Program") else 0
	total_batches = frappe.db.count("LMS Batch") if frappe.db.exists("DocType", "LMS Batch") else 0

	student_users = frappe.get_all(
		"Has Role",
		filters={"role": "LMS Student", "parenttype": "User"},
		pluck="parent",
	)
	# Distinct enrolled members as student count fallback
	enrolled_members = frappe.get_all("LMS Enrollment", pluck="member", distinct=True)
	student_set = set(student_users or []) | set(enrolled_members or [])
	student_set.discard("Guest")
	student_set.discard("Administrator")
	total_students = len(student_set)

	total_certificates = frappe.db.count("LMS Certificate")
	published_certificates = frappe.db.count("LMS Certificate", {"published": 1})

	learning_seconds = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(scorm_total_time), 0)
		FROM `tabLMS Course Progress`
		WHERE scorm_total_time IS NOT NULL
		"""
	)[0][0]
	total_learning_hours = flt(flt(learning_seconds) / 3600.0, 1)

	# SCORM packages = courses that have at least one SCORM chapter
	scorm_course_names = frappe.get_all(
		"Course Chapter",
		filters={"is_scorm_package": 1},
		pluck="course",
		distinct=True,
	)
	scorm_course_names = [n for n in scorm_course_names if n]
	total_scorm = len(scorm_course_names)
	published_scorm = (
		frappe.db.count("LMS Course", {"name": ["in", scorm_course_names], "published": 1})
		if scorm_course_names
		else 0
	)
	draft_scorm = (
		frappe.db.count("LMS Course", {"name": ["in", scorm_course_names], "published": 0})
		if scorm_course_names
		else 0
	)

	recent_scorm = []
	if scorm_course_names:
		recent_scorm = frappe.get_all(
			"LMS Course",
			filters={"name": ["in", scorm_course_names]},
			fields=["name", "title", "published", "modified", "creation"],
			order_by="modified desc",
			limit=5,
		)
		for row in recent_scorm:
			row["status"] = "Published" if row.published else "Draft"

	# Course management rows (skip demo seed course)
	courses = frappe.get_all(
		"LMS Course",
		filters=course_filters or None,
		fields=["name", "title", "published", "upcoming", "modified", "creation"],
		order_by="modified desc",
		limit=12,
	)
	course_rows = []
	for course in courses:
		enrollments = frappe.db.count("LMS Enrollment", {"course": course.name})
		completed = frappe.db.count(
			"LMS Enrollment", {"course": course.name, "progress": [">=", 100]}
		)
		completion_rate = flt((completed / enrollments) * 100, 1) if enrollments else 0
		if course.published:
			status = "Published"
		elif course.upcoming:
			status = "Upcoming"
		else:
			status = "Draft"
		course_rows.append(
			{
				"name": course.name,
				"title": course.title,
				"status": status,
				"published": course.published,
				"enrollments": enrollments,
				"completion_rate": completion_rate,
				"modified": course.modified,
			}
		)

	# Users
	total_users = frappe.db.count(
		"User", {"enabled": 1, "name": ["not in", ("Guest",)]}
	)
	active_users = frappe.db.count(
		"User",
		{
			"enabled": 1,
			"name": ["not in", ("Guest",)],
			"last_active": [">=", active_since],
		},
	)
	inactive_users = max(total_users - active_users, 0)
	new_users_month = frappe.db.count(
		"User",
		{
			"enabled": 1,
			"name": ["not in", ("Guest",)],
			"creation": [">=", month_start],
		},
	)

	# Charts — enrollment growth (last 6 months)
	month_meta = _month_labels(6)
	enrollment_growth = []
	learning_hours_trend = []
	for meta in month_meta:
		next_start = add_months(meta["start"], 1)
		enroll_count = frappe.db.count(
			"LMS Enrollment",
			{"creation": ["between", [meta["start"], add_days(next_start, -1)]]},
		)
		enrollment_growth.append({"label": meta["label"], "value": enroll_count})

		seconds = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(scorm_total_time), 0)
			FROM `tabLMS Course Progress`
			WHERE modified >= %s AND modified < %s
			""",
			(meta["start"], next_start),
		)[0][0]
		learning_hours_trend.append(
			{"label": meta["label"], "value": flt(flt(seconds) / 3600.0, 1)}
		)

	# Completion rates by course (top 6 by enrollments)
	popular = frappe.db.sql(
		"""
		SELECT course, COUNT(*) AS enrollments
		FROM `tabLMS Enrollment`
		GROUP BY course
		ORDER BY enrollments DESC
		LIMIT 6
		""",
		as_dict=True,
	)
	popular_courses = []
	completion_rates = []
	for row in popular:
		if row.course in demo_course_names:
			continue
		title = frappe.db.get_value("LMS Course", row.course, "title") or row.course
		completed = frappe.db.count(
			"LMS Enrollment", {"course": row.course, "progress": [">=", 100]}
		)
		rate = flt((completed / row.enrollments) * 100, 1) if row.enrollments else 0
		popular_courses.append(
			{"label": title, "value": row.enrollments, "course": row.course}
		)
		completion_rates.append({"label": title, "value": rate, "course": row.course})

	# Active learners weekly (last 8 weeks)
	active_learners_trend = []
	for i in range(7, -1, -1):
		week_end = add_days(today, -7 * i)
		week_begin = add_days(week_end, -6)
		count = frappe.db.count(
			"User",
			{
				"enabled": 1,
				"name": ["not in", ("Guest", "Administrator")],
				"last_active": ["between", [week_begin, week_end]],
			},
		)
		active_learners_trend.append(
			{
				"label": week_begin.strftime("%d %b"),
				"value": count,
			}
		)

	# Recent activity timeline
	activity = []
	for course in frappe.get_all(
		"LMS Course",
		filters=course_filters or None,
		fields=["name", "title", "creation", "published", "published_on", "modified"],
		order_by="creation desc",
		limit=5,
	):
		activity.append(
			{
				"type": "course_created",
				"title": _("Course Created"),
				"description": course.title,
				"when": course.creation,
				"route": {"name": "GeniusCourseDetail", "params": {"courseName": course.name}},
			}
		)
		if course.published:
			activity.append(
				{
					"type": "course_published",
					"title": _("Course Published"),
					"description": course.title,
					"when": course.published_on or course.modified,
					"route": {"name": "GeniusCourseDetail", "params": {"courseName": course.name}},
				}
			)

	for course in recent_scorm[:3]:
		activity.append(
			{
				"type": "scorm_uploaded",
				"title": _("SCORM Uploaded"),
				"description": course.title,
				"when": course.creation or course.modified,
				"route": {"name": "GeniusCourseDetail", "params": {"courseName": course.name}},
			}
		)

	for user in frappe.get_all(
		"User",
		filters={"name": ["not in", ("Guest", "Administrator")]},
		fields=["name", "full_name", "creation"],
		order_by="creation desc",
		limit=5,
	):
		activity.append(
			{
				"type": "user_registered",
				"title": _("User Registered"),
				"description": user.full_name or user.name,
				"when": user.creation,
			}
		)

	for cert in frappe.get_all(
		"LMS Certificate",
		fields=["name", "member_name", "course", "issue_date", "creation"],
		order_by="creation desc",
		limit=5,
	):
		course_title = frappe.db.get_value("LMS Course", cert.course, "title") or cert.course
		activity.append(
			{
				"type": "certificate_generated",
				"title": _("Certificate Generated"),
				"description": f"{cert.member_name or ''} · {course_title}".strip(" ·"),
				"when": cert.issue_date or cert.creation,
			}
		)

	def _activity_ts(item):
		when = item.get("when")
		if not when:
			return now_datetime()
		try:
			return get_datetime(when)
		except Exception:
			return now_datetime()

	activity.sort(key=_activity_ts, reverse=True)
	activity = activity[:12]

	# Notifications / alerts (best-effort from real data)
	pending_reviews = frappe.db.count("LMS Assignment Submission", {"status": "Not Graded"}) if frappe.db.exists("DocType", "LMS Assignment Submission") else 0
	# Draft courses awaiting publish as "pending approvals"
	pending_approvals = draft_courses
	failed_scorm = 0  # No durable failed-upload log yet
	system_alerts = []
	if draft_courses:
		system_alerts.append(
			{
				"type": "info",
				"title": _("Draft courses"),
				"description": _("{0} course(s) are still in draft").format(draft_courses),
			}
		)
	if pending_reviews:
		system_alerts.append(
			{
				"type": "warning",
				"title": _("Pending reviews"),
				"description": _("{0} assignment submission(s) need grading").format(pending_reviews),
			}
		)

	courses_this_month = frappe.db.count(
		"LMS Course", {**course_filters, "creation": [">=", month_start]}
	)
	courses_prev_month = frappe.db.count(
		"LMS Course",
		{
			**course_filters,
			"creation": ["between", [prev_month_start, add_days(month_start, -1)]],
		},
	)

	return {
		"kpis": {
			"total_courses": total_courses,
			"published_courses": published_courses,
			"draft_courses": draft_courses,
			"total_programs": total_programs,
			"total_batches": total_batches,
			"total_students": total_students,
			"total_certificates": published_certificates or total_certificates,
			"total_learning_hours": total_learning_hours,
			"courses_delta": courses_this_month - courses_prev_month,
			"prev_total_courses": prev_total_courses,
		},
		"scorm": {
			"total": total_scorm,
			"published": published_scorm,
			"draft": draft_scorm,
			"recent": recent_scorm,
		},
		"courses": course_rows,
		"users": {
			"total": total_users,
			"active": active_users,
			"inactive": inactive_users,
			"new_this_month": new_users_month,
		},
		"charts": {
			"enrollment_growth": enrollment_growth,
			"completion_rates": completion_rates,
			"popular_courses": popular_courses,
			"active_learners": active_learners_trend,
			"learning_hours": learning_hours_trend,
		},
		"activity": activity,
		"notifications": {
			"pending_reviews": pending_reviews,
			"pending_approvals": pending_approvals,
			"failed_scorm_uploads": failed_scorm,
			"alerts": system_alerts,
		},
		"generated_at": str(now_datetime()),
	}


@frappe.whitelist()
def get_analytics_chart_filters():
	"""Course and batch options for analytics chart filters."""
	_ensure_analytics_access()

	courses = frappe.get_all(
		"LMS Course",
		fields=["name", "title"],
		order_by="title asc",
	)
	batches = frappe.get_all(
		"LMS Batch",
		fields=["name", "title"],
		order_by="start_date desc",
	)

	return {"courses": courses, "batches": batches}


def _is_all_filter(value) -> bool:
	return not value or cstr(value) in ("__all__", "All")


def _get_all_batch_names() -> list:
	return frappe.get_all("LMS Batch", pluck="name", order_by="start_date desc")


def _get_all_course_names() -> list:
	return frappe.get_all("LMS Course", pluck="name", order_by="title asc")


def _has_lms_batches() -> bool:
	return bool(frappe.db.count("LMS Batch"))


def _get_course_enrolled_members() -> list:
	"""Unique learners enrolled in any course (course-centric analytics)."""
	members = frappe.get_all("LMS Enrollment", pluck="member")
	return list(dict.fromkeys(members))


def _member_course_status(member: str) -> str:
	"""Best status across all course enrollments for a learner."""
	if frappe.db.exists("LMS Certificate", {"member": member, "published": 1}):
		return "completed"

	enrollments = frappe.get_all(
		"LMS Enrollment",
		filters={"member": member},
		fields=["course", "progress"],
	)
	if not enrollments:
		return "not_started"

	progress_values = [flt(row.progress or 0) for row in enrollments]
	if progress_values and (sum(progress_values) / len(progress_values)) >= 100:
		return "completed"
	if any(p >= 100 for p in progress_values):
		return "completed"
	if any(p > 0 for p in progress_values):
		return "in_progress"
	if frappe.db.exists("LMS Course Progress", {"member": member}):
		return "in_progress"
	return "not_started"


def _course_learner_status_counts() -> dict:
	counts = {"completed": 0, "in_progress": 0, "not_started": 0}
	for member in _get_course_enrolled_members():
		counts[_member_course_status(member)] += 1
	return counts


def _course_learner_status_counts_as_of(as_of_date) -> dict:
	"""Approximate historical status using certificates issued by date + live enrollment."""
	from frappe.utils import getdate

	as_of = getdate(as_of_date)
	counts = {"completed": 0, "in_progress": 0, "not_started": 0}
	certified_members = set(
		frappe.get_all(
			"LMS Certificate",
			filters={"published": 1, "issue_date": ["<=", as_of]},
			pluck="member",
		)
	)
	for member in _get_course_enrolled_members():
		if member in certified_members:
			counts["completed"] += 1
			continue
		status = _member_course_status(member)
		# Past months: only count completed via certificate; treat others as not started
		# so the chart still has a stable series. Current-month callers use live counts.
		if status == "completed":
			counts["completed"] += 1
		else:
			counts["not_started"] += 1
	return counts


def _should_use_course_analytics(batch: str | None) -> bool:
	"""Use course enrollments when All is selected and no LMS batches exist."""
	return _is_all_filter(batch) and not _has_lms_batches()


def _lesson_chart_label(title: str) -> str:
	if not title:
		return ""
	first_word = title.split()[0]
	if len(first_word) <= 10:
		return first_word
	return title[:10]


def _get_course_lessons_ordered(course: str) -> list:
	LessonReference = frappe.qb.DocType("Lesson Reference")
	ChapterReference = frappe.qb.DocType("Chapter Reference")
	Lesson = frappe.qb.DocType("Course Lesson")

	rows = (
		frappe.qb.from_(LessonReference)
		.join(ChapterReference)
		.on(LessonReference.parent == ChapterReference.chapter)
		.join(Lesson)
		.on(LessonReference.lesson == Lesson.name)
		.select(Lesson.name, Lesson.title)
		.where(ChapterReference.parent == course)
		.orderby(ChapterReference.idx, LessonReference.idx)
		.run(as_dict=True)
	)

	for row in rows:
		row["label"] = _lesson_chart_label(row.title)

	return rows


@frappe.whitelist()
def get_analytics_lesson_completion(course: str = None):
	"""Per-lesson completion rate (%) for enrolled students in a course."""
	_ensure_analytics_access()

	if _is_all_filter(course):
		course_names = _get_all_course_names()
		chart_data = []
		enrolled_count = 0

		for course_name in course_names:
			course_title = frappe.db.get_value("LMS Course", course_name, "title") or course_name
			course_enrolled = frappe.db.count("LMS Enrollment", {"course": course_name})
			enrolled_count += course_enrolled
			lessons = _get_course_lessons_ordered(course_name)

			for lesson in lessons:
				completed_count = frappe.db.count(
					"LMS Course Progress",
					{"course": course_name, "lesson": lesson.name, "status": "Complete"},
				)
				completion_rate = (
					flt((completed_count / course_enrolled) * 100, 1) if course_enrolled else 0
				)
				label = lesson.label
				if len(course_names) > 1:
					course_short = _lesson_chart_label(course_title)
					label = f"{label} ({course_short})" if course_short else label
				chart_data.append(
					{
						"lesson": lesson.name,
						"label": label,
						"title": lesson.title,
						"course": course_name,
						"completion": completion_rate,
					}
				)

		return {
			"course": "__all__",
			"enrolled_count": enrolled_count,
			"lessons": chart_data,
		}

	if not frappe.db.exists("LMS Course", course):
		frappe.throw(_("Course not found"))

	enrolled_count = frappe.db.count("LMS Enrollment", {"course": course})
	lessons = _get_course_lessons_ordered(course)
	chart_data = []

	for lesson in lessons:
		completed_count = frappe.db.count(
			"LMS Course Progress",
			{"course": course, "lesson": lesson.name, "status": "Complete"},
		)
		completion_rate = flt((completed_count / enrolled_count) * 100, 1) if enrolled_count else 0
		chart_data.append(
			{
				"lesson": lesson.name,
				"label": lesson.label,
				"title": lesson.title,
				"completion": completion_rate,
			}
		)

	return {
		"course": course,
		"enrolled_count": enrolled_count,
		"lessons": chart_data,
	}


def _format_week_range_label(week_start, week_end) -> str:
	"""Compact axis label, e.g. Jun 1–7 or May 30–Jun 5."""
	from frappe.utils import formatdate

	start_fmt = formatdate(week_start, "MMM d")
	if week_start.month == week_end.month:
		end_fmt = formatdate(week_end, "d")
	else:
		end_fmt = formatdate(week_end, "MMM d")
	return f"{start_fmt}–{end_fmt}"


def _format_week_range_tooltip(week_start, week_end) -> str:
	"""Full tooltip range with year, e.g. Jun 1, 2026 – Jun 7, 2026."""
	from frappe.utils import formatdate

	start_fmt = formatdate(week_start, "medium")
	end_fmt = formatdate(week_end, "medium")
	return f"{start_fmt} – {end_fmt}"


@frappe.whitelist()
def get_analytics_active_learners_trend(batch: str = None, weeks: int = 8):
	"""Weekly count of members active (last_active) per week.

	Each week is a rolling 7-day window (inclusive) counting backward from today.
	The oldest window is returned first; the newest window ends on today.
	Uses batch enrollments when batches exist; otherwise course enrollments.
	"""
	_ensure_analytics_access()

	if _should_use_course_analytics(batch):
		batch = "__all__"
		members = _get_course_enrolled_members()
	elif _is_all_filter(batch):
		batch = "__all__"
		members = frappe.get_all("LMS Batch Enrollment", pluck="member")
		members = list(dict.fromkeys(members))
	elif not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))
	else:
		members = frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member")

	weeks = cint(weeks) or 8

	period_description = _(
		"Each point is a 7-day window rolling back from today; the rightmost week includes today."
	)

	if not members:
		return {"batch": batch, "weeks": [], "period_description": period_description}

	from frappe.utils import add_days, get_datetime, getdate

	today = getdate()
	chart_data = []

	for week_index in range(weeks):
		week_end = add_days(today, -(weeks - 1 - week_index) * 7)
		week_start = add_days(week_end, -6)
		active_count = frappe.db.count(
			"User",
			{
				"name": ["in", members],
				"enabled": 1,
				"last_active": [
					"between",
					[get_datetime(week_start), get_datetime(add_days(week_end, 1))],
				],
			},
		)
		chart_data.append(
			{
				"week": _format_week_range_label(week_start, week_end),
				"week_start": str(week_start),
				"week_end": str(week_end),
				"week_range": _format_week_range_tooltip(week_start, week_end),
				"learners": active_count,
			}
		)

	return {"batch": batch, "weeks": chart_data, "period_description": period_description}


def _get_batch_members_and_courses(batch: str):
	members = frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member")
	courses = frappe.get_all("Batch Course", filters={"parent": batch}, pluck="course")
	return members, courses


def _learner_batch_progress_status(member: str, courses: list, batch: str) -> str:
	if frappe.db.exists(
		"LMS Certificate",
		{"member": member, "batch_name": batch, "published": 1},
	):
		return "completed"

	progress_values = []
	for course in courses or []:
		progress = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "progress")
		progress_values.append(flt(progress or 0))

	if progress_values:
		avg_progress = sum(progress_values) / len(progress_values)
		if avg_progress >= 100:
			return "completed"

	if _learner_has_started_batch(member, courses, batch):
		return "in_progress"

	return "not_started"


def _batch_learner_status_counts(batch: str) -> dict:
	members, courses = _get_batch_members_and_courses(batch)
	counts = {"completed": 0, "in_progress": 0, "not_started": 0}

	for member in members:
		status = _learner_batch_progress_status(member, courses, batch)
		counts[status] += 1

	return counts


def _all_batches_learner_status_counts() -> dict:
	counts = {"completed": 0, "in_progress": 0, "not_started": 0}
	for batch in _get_all_batch_names():
		batch_counts = _batch_learner_status_counts(batch)
		for key in counts:
			counts[key] += batch_counts[key]
	return counts


def _learner_status_as_of(member: str, courses: list, batch: str, as_of_date) -> str:
	"""Learner status for a batch as of a given date (inclusive).

	Mirrors `_learner_batch_progress_status` so chart points match the summary legend:
	certified = published certificate (issued by as_of) OR avg progress >= 100.
	"""
	from frappe.utils import getdate

	as_of = getdate(as_of_date)
	certs = frappe.get_all(
		"LMS Certificate",
		filters={
			"member": member,
			"batch_name": batch,
			"published": 1,
		},
		fields=["issue_date", "creation"],
		limit=5,
	)
	for cert in certs:
		cert_date = getdate(cert.issue_date or cert.creation)
		if cert_date <= as_of:
			return "completed"

	progress_values = []
	started = False
	for course in courses or []:
		enrollment = frappe.db.get_value(
			"LMS Enrollment",
			{"member": member, "course": course},
			["progress", "creation"],
			as_dict=True,
		)
		if not enrollment or getdate(enrollment.creation) > as_of:
			progress_rows = frappe.get_all(
				"LMS Course Progress",
				filters={
					"course": course,
					"member": member,
					"creation": ["<=", as_of],
				},
				limit=1,
			)
			if progress_rows:
				started = True
			continue

		progress = flt(enrollment.progress or 0)
		progress_values.append(progress)
		if progress > 0:
			started = True

		progress_rows = frappe.get_all(
			"LMS Course Progress",
			filters={
				"course": course,
				"member": member,
				"creation": ["<=", as_of],
			},
			limit=1,
		)
		if progress_rows:
			started = True

	if progress_values:
		avg_progress = sum(progress_values) / len(progress_values)
		if avg_progress >= 100:
			return "completed"

	if started:
		return "in_progress"

	return "not_started"


def _batch_learner_status_counts_as_of(batch: str, as_of_date) -> dict:
	from frappe.utils import getdate

	as_of = getdate(as_of_date)
	courses = frappe.get_all("Batch Course", filters={"parent": batch}, pluck="course")
	enrollments = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"batch": batch, "creation": ["<=", as_of]},
		pluck="member",
	)
	counts = {"completed": 0, "in_progress": 0, "not_started": 0}
	for member in enrollments:
		status = _learner_status_as_of(member, courses, batch, as_of)
		counts[status] += 1
	return counts


def _learner_status_counts_as_of(batch: str, as_of_date) -> dict:
	if batch == "__all__":
		counts = {"completed": 0, "in_progress": 0, "not_started": 0}
		for batch_name in _get_all_batch_names():
			batch_counts = _batch_learner_status_counts_as_of(batch_name, as_of_date)
			for key in counts:
				counts[key] += batch_counts[key]
		return counts
	return _batch_learner_status_counts_as_of(batch, as_of_date)


@frappe.whitelist()
def get_analytics_course_status_breakdown(batch: str = None):
	"""Donut chart data: learner status distribution for a batch or all courses."""
	_ensure_analytics_access()

	if _should_use_course_analytics(batch):
		batch = "__all__"
		counts = _course_learner_status_counts()
	elif _is_all_filter(batch):
		batch = "__all__"
		counts = _all_batches_learner_status_counts()
	elif not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))
	else:
		counts = _batch_learner_status_counts(batch)

	total = sum(counts.values())

	segments = [
		{
			"label": _("Completed"),
			"status_key": "completed",
			"value": counts["completed"],
			"percent": cint((counts["completed"] / total) * 100) if total else 0,
		},
		{
			"label": _("In progress"),
			"status_key": "in_progress",
			"value": counts["in_progress"],
			"percent": cint((counts["in_progress"] / total) * 100) if total else 0,
		},
		{
			"label": _("Not started"),
			"status_key": "not_started",
			"value": counts["not_started"],
			"percent": cint((counts["not_started"] / total) * 100) if total else 0,
		},
	]

	return {"batch": batch, "total": total, "segments": segments}


@frappe.whitelist()
def get_analytics_certifications_trend(batch: str = None, months: int = 6):
	"""Monthly certifications issued for a batch/course with summary counts."""
	_ensure_analytics_access()

	use_courses = _should_use_course_analytics(batch)
	if use_courses or _is_all_filter(batch):
		batch = "__all__"
	elif not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))

	from frappe.utils import add_months, formatdate, get_first_day, getdate

	months = cint(months) or 6
	if use_courses:
		counts = _course_learner_status_counts()
	else:
		counts = (
			_all_batches_learner_status_counts()
			if batch == "__all__"
			else _batch_learner_status_counts(batch)
		)
	summary = {
		"certified": counts["completed"],
		"in_progress": counts["in_progress"],
		"not_started": counts["not_started"],
	}

	today = getdate()
	chart_data = []

	for month_index in range(months - 1, -1, -1):
		month_start = get_first_day(add_months(today, -month_index))
		next_month_start = get_first_day(add_months(month_start, 1))
		month_end = add_days(next_month_start, -1)

		# Current month must match the legend summary exactly.
		if month_index == 0:
			status_as_of = counts
		elif use_courses:
			status_as_of = _course_learner_status_counts_as_of(month_end)
		else:
			status_as_of = _learner_status_counts_as_of(batch, month_end)

		cert_filters = {
			"published": 1,
			"issue_date": ["between", [month_start, month_end]],
		}
		if batch != "__all__":
			cert_filters["batch_name"] = batch

		certificates = frappe.get_all(
			"LMS Certificate",
			filters=cert_filters,
			fields=["course", "course_title"],
		)
		course_counts = {}
		for cert in certificates:
			title = cert.course_title or cert.course or _("Untitled course")
			course_counts[title] = course_counts.get(title, 0) + 1

		courses_breakdown = [
			{"title": title, "certified": count}
			for title, count in sorted(
				course_counts.items(), key=lambda item: (-item[1], item[0])
			)
		]

		chart_data.append(
			{
				"month": formatdate(month_start, "MMM"),
				"period": formatdate(month_start, "MMM yyyy"),
				"certified": status_as_of["completed"],
				"in_progress": status_as_of["in_progress"],
				"not_started": status_as_of["not_started"],
				"certificates_issued": len(certificates),
				"courses": courses_breakdown,
			}
		)

	return {"batch": batch, "summary": summary, "months": chart_data}


def _relative_last_active(last_active) -> str:
	if not last_active:
		return _("Never")

	from frappe.utils import format_datetime, now_datetime, time_diff_in_hours

	hours = time_diff_in_hours(now_datetime(), get_datetime(last_active))
	if hours < 1:
		return _("Today")
	if hours < 24:
		return _("Today")
	days = int(hours / 24)
	if days == 1:
		return _("1 day ago")
	if days < 7:
		return _("{0} days ago").format(days)
	return format_datetime(last_active, "dd MMM YYYY")


def _learner_has_started_batch(member: str, courses: list, batch: str) -> bool:
	"""True if the learner has any measurable activity on this batch."""
	for course in courses or []:
		if flt(
			frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "progress") or 0
		) > 0:
			return True
		if frappe.db.exists("LMS Course Progress", {"course": course, "member": member}):
			return True

	if _learner_batch_assessment_counts(member, batch)["attempted"] > 0:
		return True

	if _learner_quiz_average(member, batch) is not None:
		return True

	return False


def _learner_display_status(member: str, courses: list, batch: str):
	"""Return (filter_key, display_label) for learner progress table."""
	has_cert = frappe.db.exists(
		"LMS Certificate",
		{"member": member, "batch_name": batch, "published": 1},
	)

	if has_cert:
		return "certified", _("Certified")

	if _learner_has_started_batch(member, courses, batch):
		return "in_progress", _("In progress")

	return "not_started", _("Not started")


def _learner_quiz_average(member: str, batch: str):
	quiz_names = frappe.get_all(
		"LMS Assessment",
		filters={"parent": batch, "assessment_type": "LMS Quiz"},
		pluck="assessment_name",
	)
	if not quiz_names:
		return None

	percentages = []
	for quiz in quiz_names:
		submissions = frappe.get_all(
			"LMS Quiz Submission",
			filters={"quiz": quiz, "member": member},
			fields=["percentage"],
			order_by="creation desc",
			limit=1,
		)
		if submissions and submissions[0].percentage is not None:
			percentages.append(flt(submissions[0].percentage))

	if not percentages:
		return None

	return cint(sum(percentages) / len(percentages))


def _iter_learner_batch_assessment_rows(member: str, batch: str):
	"""Yield attempted/passed state for each LMS Assessment on a batch."""
	from lms.lms.utils import has_submitted_assessment

	assessments = frappe.get_all(
		"LMS Assessment",
		filters={"parent": batch},
		fields=["assessment_type", "assessment_name"],
	)
	for assessment in assessments:
		info = has_submitted_assessment(
			assessment.assessment_name, assessment.assessment_type, member
		)
		attempted = bool(info.get("submission"))
		yield {
			"assessment": assessment,
			"info": info,
			"attempted": attempted,
			"passed": info.result in ("Pass", "Passed") if attempted else False,
		}


def _learner_batch_assessment_counts(member: str, batch: str) -> dict:
	rows = list(_iter_learner_batch_assessment_rows(member, batch))
	total = len(rows)
	attempted = sum(1 for row in rows if row["attempted"])
	passed = sum(1 for row in rows if row["attempted"] and row["passed"])
	return {"total": total, "attempted": attempted, "passed": passed}


def _learner_assessment_label(member: str, batch: str) -> str:
	"""Summary of batch assessments (quizzes, assignments, etc.) for the analytics table."""
	counts = _learner_batch_assessment_counts(member, batch)
	total = counts["total"]
	attempted = counts["attempted"]
	passed = counts["passed"]

	if not total:
		return "—"

	if attempted == 0:
		return _("Not attempted")

	return _("{0}/{1} passed").format(passed, total)


def _learner_mock_status(member: str, batch: str) -> str:
	from lms.lms.mock_assessment import learner_mock_status_label

	return learner_mock_status_label(member, batch)


@frappe.whitelist()
def get_analytics_learner_progress(
	batch: str = None,
	status_filter: str = "All",
	page: int = 1,
	page_length: int = 20,
	search: str = None,
):
	"""Learner progress rows for a batch (or all course enrollments when no batches)."""
	_ensure_analytics_access()

	if _should_use_course_analytics(batch):
		return _get_analytics_learner_progress_from_courses(
			status_filter=status_filter,
			page=page,
			page_length=page_length,
			search=search,
		)

	if _is_all_filter(batch):
		batch = "__all__"
	elif not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))

	page = max(cint(page) or 1, 1)
	page_length = min(max(cint(page_length) or 20, 1), 100)
	search_term = (search or "").strip().lower()

	batch_names = _get_all_batch_names() if batch == "__all__" else [batch]
	rows_by_member = {}
	rows = []

	for batch_name in batch_names:
		batch_title = frappe.db.get_value("LMS Batch", batch_name, "title") or batch_name
		members = frappe.get_all(
			"LMS Batch Enrollment",
			filters={"batch": batch_name},
			fields=["member", "member_name"],
			order_by="member_name asc",
		)
		courses = frappe.get_all("Batch Course", filters={"parent": batch_name}, pluck="course")
		total_lessons = 0
		for course in courses:
			try:
				total_lessons += cint(get_lessons(course, get_details=False) or 0)
			except Exception:
				continue

		for enrollment in members:
			member = enrollment.get("member") if isinstance(enrollment, dict) else enrollment.member
			member_name = (
				enrollment.get("member_name") if isinstance(enrollment, dict) else enrollment.member_name
			)
			user = frappe.db.get_value(
				"User",
				member,
				["full_name", "user_image", "username", "email", "last_active"],
				as_dict=True,
			)
			if not user:
				continue

			full_name = user.full_name or member_name or ""
			if search_term:
				searchable = " ".join(
					[
						full_name,
						user.username or "",
						user.email or "",
						member or "",
						member_name or "",
					]
				).lower()
				if search_term not in searchable:
					continue

			completed_lessons = 0
			progress_values = []
			for course in courses:
				completed_lessons += frappe.db.count(
					"LMS Course Progress",
					{"course": course, "member": member, "status": "Complete"},
				)
				progress = frappe.db.get_value(
					"LMS Enrollment", {"member": member, "course": course}, "progress"
				)
				progress_values.append(flt(progress or 0))

			avg_progress = cint(sum(progress_values) / len(progress_values)) if progress_values else 0
			filter_key, status_label = _learner_display_status(member, courses, batch_name)
			quiz_average = _learner_quiz_average(member, batch_name)

			if batch == "__all__":
				row = rows_by_member.setdefault(
					member,
					{
						"member": member,
						"full_name": full_name,
						"user_image": user.user_image,
						"username": user.username,
						"batch": batch_name,
						"batch_title": [],
						"lessons_completed": 0,
						"lessons_total": 0,
						"_progress_values": [],
						"_quiz_values": [],
						"_assessment_total": 0,
						"_assessment_attempted": 0,
						"_assessment_passed": 0,
						"_mock_labels": [],
						"_status_priority": 0,
						"last_active": _relative_last_active(user.last_active),
					},
				)
				row["batch_title"].append(batch_title)
				row["lessons_completed"] += completed_lessons
				row["lessons_total"] += total_lessons
				row["_progress_values"].extend(progress_values)
				if quiz_average is not None:
					row["_quiz_values"].append(quiz_average)
				assessment_counts = _learner_batch_assessment_counts(member, batch_name)
				row["_assessment_total"] += assessment_counts["total"]
				row["_assessment_attempted"] += assessment_counts["attempted"]
				row["_assessment_passed"] += assessment_counts["passed"]
				mock_label = _learner_mock_status(member, batch_name)
				if mock_label and mock_label != "—":
					row["_mock_labels"].append(mock_label)
				priority = {"certified": 3, "in_progress": 2, "not_started": 1}.get(filter_key, 0)
				if priority > row["_status_priority"]:
					row["_status_priority"] = priority
					row["status"] = status_label
					row["status_key"] = filter_key
			else:
				rows.append(
					{
						"member": member,
						"full_name": full_name,
						"user_image": user.user_image,
						"username": user.username,
						"batch": batch_name,
						"batch_title": batch_title,
						"lessons_completed": completed_lessons,
						"lessons_total": total_lessons,
						"progress": avg_progress,
						"quiz_results": quiz_average,
						"assessment": _learner_assessment_label(member, batch_name),
						"mock": _learner_mock_status(member, batch_name),
						"status": status_label,
						"status_key": filter_key,
						"last_active": _relative_last_active(user.last_active),
					}
				)

	if batch == "__all__":
		for row in rows_by_member.values():
			progress_values = row.pop("_progress_values")
			quiz_values = row.pop("_quiz_values")
			assessment_total = row.pop("_assessment_total")
			assessment_attempted = row.pop("_assessment_attempted")
			assessment_passed = row.pop("_assessment_passed")
			mock_labels = list(dict.fromkeys(row.pop("_mock_labels")))
			row.pop("_status_priority", None)
			row["batch_title"] = ", ".join(dict.fromkeys(row["batch_title"]))
			row["progress"] = cint(sum(progress_values) / len(progress_values)) if progress_values else 0
			row["quiz_results"] = cint(sum(quiz_values) / len(quiz_values)) if quiz_values else None
			if not assessment_total:
				row["assessment"] = "—"
			elif assessment_attempted == 0:
				row["assessment"] = _("Not attempted")
			else:
				row["assessment"] = _("{0}/{1} passed").format(assessment_passed, assessment_total)
			row["mock"] = mock_labels[0] if len(mock_labels) == 1 else "—"
			rows.append(row)

	filter_map = {
		"Certified": "certified",
		"In progress": "in_progress",
		"Not started": "not_started",
	}
	if status_filter and status_filter != "All":
		selected_status = filter_map.get(status_filter, status_filter.lower().replace(" ", "_"))
		rows = [row for row in rows if row.get("status_key") == selected_status]

	rows.sort(key=lambda row: ((row.get("full_name") or "").lower(), (row.get("username") or "").lower()))

	total_count = len(rows)
	start = (page - 1) * page_length
	end = start + page_length

	return {
		"batch": batch,
		"learners": rows[start:end],
		"total_count": total_count,
		"page": page,
		"page_length": page_length,
	}


def _get_analytics_learner_progress_from_courses(
	status_filter: str = "All",
	page: int = 1,
	page_length: int = 20,
	search: str = None,
):
	"""Learner progress from LMS Enrollment when the site has no batches."""
	page = max(cint(page) or 1, 1)
	page_length = min(max(cint(page_length) or 20, 1), 100)
	search_term = (search or "").strip().lower()

	enrollments = frappe.get_all(
		"LMS Enrollment",
		fields=["member", "member_name", "course", "progress"],
		order_by="member_name asc",
	)

	rows_by_member = {}
	for enrollment in enrollments:
		member = enrollment.member
		user = frappe.db.get_value(
			"User",
			member,
			["full_name", "user_image", "username", "email", "last_active"],
			as_dict=True,
		)
		if not user:
			continue

		full_name = user.full_name or enrollment.member_name or ""
		if search_term:
			searchable = " ".join(
				[
					full_name,
					user.username or "",
					user.email or "",
					member or "",
					enrollment.member_name or "",
				]
			).lower()
			if search_term not in searchable:
				continue

		course_title = (
			frappe.db.get_value("LMS Course", enrollment.course, "title") or enrollment.course
		)
		try:
			lessons_total = cint(get_lessons(enrollment.course, get_details=False) or 0)
		except Exception:
			lessons_total = 0
		lessons_completed = frappe.db.count(
			"LMS Course Progress",
			{"course": enrollment.course, "member": member, "status": "Complete"},
		)

		status_map = {
			"completed": ("certified", _("Certified")),
			"in_progress": ("in_progress", _("In progress")),
			"not_started": ("not_started", _("Not started")),
		}
		raw_status = _member_course_status(member)
		filter_key, status_label = status_map[raw_status]

		row = rows_by_member.setdefault(
			member,
			{
				"member": member,
				"full_name": full_name,
				"user_image": user.user_image,
				"username": user.username,
				"batch": None,
				"batch_title": [],
				"lessons_completed": 0,
				"lessons_total": 0,
				"_progress_values": [],
				"quiz_results": None,
				"assessment": "—",
				"mock": "—",
				"_status_priority": 0,
				"last_active": _relative_last_active(user.last_active),
			},
		)
		row["batch_title"].append(course_title)
		row["lessons_completed"] += lessons_completed
		row["lessons_total"] += lessons_total
		row["_progress_values"].append(flt(enrollment.progress or 0))
		priority = {"certified": 3, "in_progress": 2, "not_started": 1}.get(filter_key, 0)
		if priority > row["_status_priority"]:
			row["_status_priority"] = priority
			row["status"] = status_label
			row["status_key"] = filter_key

	rows = []
	for row in rows_by_member.values():
		progress_values = row.pop("_progress_values")
		row.pop("_status_priority", None)
		row["batch_title"] = ", ".join(dict.fromkeys(row["batch_title"]))
		row["progress"] = cint(sum(progress_values) / len(progress_values)) if progress_values else 0
		rows.append(row)

	filter_map = {
		"Certified": "certified",
		"In progress": "in_progress",
		"Not started": "not_started",
	}
	if status_filter and status_filter != "All":
		selected_status = filter_map.get(status_filter, status_filter.lower().replace(" ", "_"))
		rows = [row for row in rows if row.get("status_key") == selected_status]

	rows.sort(key=lambda row: ((row.get("full_name") or "").lower(), (row.get("username") or "").lower()))

	total_count = len(rows)
	start = (page - 1) * page_length
	end = start + page_length

	return {
		"batch": "__all__",
		"learners": rows[start:end],
		"total_count": total_count,
		"page": page,
		"page_length": page_length,
	}


def _ensure_batch_student_access(batch: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("You must be logged in to view the leaderboard."), frappe.PermissionError)

	if not batch:
		frappe.throw(_("Batch is required"))

	if not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))

	if not frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": frappe.session.user}):
		frappe.throw(_("You are not enrolled in this batch."), frappe.PermissionError)


def _get_batch_total_lessons(batch: str) -> int:
	courses = frappe.get_all("Batch Course", filters={"parent": batch}, pluck="course")
	total_lessons = 0
	for course in courses:
		try:
			total_lessons += cint(get_lessons(course, get_details=False) or 0)
		except Exception:
			continue
	return total_lessons


def _get_member_lessons_completed(member: str, courses: list) -> int:
	completed_lessons = 0
	for course in courses or []:
		completed_lessons += frappe.db.count(
			"LMS Course Progress",
			{"course": course, "member": member, "status": "Complete"},
		)
	return completed_lessons


@frappe.whitelist()
def get_batch_leaderboard(batch: str):
	"""Return batch metadata and per-member lesson progress for the student leaderboard."""
	_ensure_batch_student_access(batch)

	batch_doc = frappe.db.get_value(
		"LMS Batch",
		batch,
		["title", "start_date"],
		as_dict=True,
	)
	courses = frappe.get_all("Batch Course", filters={"parent": batch}, fields=["course", "title"])
	course_names = [row.course for row in courses]
	total_lessons = _get_batch_total_lessons(batch)

	members = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"batch": batch},
		fields=["member", "member_name"],
	)

	batchmates = []
	for enrollment in members:
		member = enrollment.member
		user = frappe.db.get_value(
			"User",
			member,
			["full_name", "name"],
			as_dict=True,
		)
		if not user:
			continue

		lessons_completed = _get_member_lessons_completed(member, course_names)
		completion_pct = flt((lessons_completed / total_lessons) * 100, 1) if total_lessons else 0

		batchmates.append(
			{
				"user_id": member,
				"full_name": user.full_name or enrollment.member_name or member,
				"lessons_completed": lessons_completed,
				"completion_pct": completion_pct,
				"is_current_user": member == frappe.session.user,
			}
		)

	course_name = courses[0].title if courses else ""

	return {
		"batch_name": batch_doc.title,
		"course_name": course_name,
		"start_date": batch_doc.start_date,
		"total_members": len(batchmates),
		"total_lessons": total_lessons,
		"batchmates": batchmates,
	}


def _get_or_create_learner_review(batch: str, member: str):
	name = frappe.db.get_value("LMS Learner Review", {"batch": batch, "member": member})
	if name:
		return frappe.get_doc("LMS Learner Review", name)

	doc = frappe.new_doc("LMS Learner Review")
	doc.batch = batch
	doc.member = member
	doc.insert(ignore_permissions=True)
	return doc


def _default_mock_rating(member: str, batch: str):
	evaluation = frappe.get_all(
		"LMS Certificate Evaluation",
		filters={"member": member, "batch_name": batch},
		fields=["rating"],
		order_by="modified desc",
		limit=1,
	)
	if not evaluation or evaluation[0].rating is None:
		return None

	rating = flt(evaluation[0].rating)
	if rating <= 1:
		return flt(rating * 5, 1)
	return flt(rating, 1)


def _learner_assessment_results(member: str, batch: str) -> list:
	type_labels = {
		"LMS Quiz": "Quiz",
		"LMS Assignment": "Assignment",
		"LMS Programming Exercise": "Programming",
	}
	results = []

	for row in _iter_learner_batch_assessment_rows(member, batch):
		assessment = row["assessment"]
		info = row["info"]
		passed = row["passed"]
		title = frappe.db.get_value(
			assessment.assessment_type, assessment.assessment_name, "title"
		)
		score = None
		score_display = "—"
		has_attempt = False
		attempt_count = 0

		if assessment.assessment_type == "LMS Quiz":
			submissions = frappe.get_all(
				"LMS Quiz Submission",
				filters={"quiz": assessment.assessment_name, "member": member},
				fields=["score", "score_out_of", "percentage"],
				order_by="creation desc",
			)
			attempt_count = len(submissions)
			has_attempt = attempt_count > 0
			if submissions:
				sub = submissions[0]
				if sub.score is not None and sub.score_out_of:
					score_display = f"{cint(sub.score)}/{cint(sub.score_out_of)}"
					score = cint(sub.score)
		elif assessment.assessment_type == "LMS Programming Exercise":
			submissions = frappe.get_all(
				"LMS Programming Exercise Submission",
				filters={"exercise": assessment.assessment_name, "member": member},
				pluck="name",
			)
			attempt_count = len(submissions)
			has_attempt = attempt_count > 0
			if has_attempt and info.status and info.status not in ("Not Attempted", 0, "0"):
				if isinstance(info.status, (int, float)) or (
					isinstance(info.status, str) and info.status.replace(".", "", 1).isdigit()
				):
					score = cint(flt(info.status))
					score_display = cstr(score)
				else:
					score_display = cstr(info.status)
		elif assessment.assessment_type == "LMS Assignment":
			submissions = frappe.get_all(
				"LMS Assignment Submission",
				filters={"assignment": assessment.assessment_name, "member": member},
				pluck="name",
			)
			attempt_count = len(submissions)
			has_attempt = attempt_count > 0
			score_display = cstr(info.status) if has_attempt and info.status else _("Not Attempted")
		else:
			score_display = cstr(info.status) if info.status else _("Not Attempted")

		results.append(
			{
				"title": title,
				"type": type_labels.get(assessment.assessment_type, assessment.assessment_type),
				"assessment_type": assessment.assessment_type,
				"assessment_name": assessment.assessment_name,
				"score": score,
				"score_display": score_display,
				"passed": passed,
				"status_label": "passed" if passed else "failed",
				"has_attempt": has_attempt,
				"attempt_count": attempt_count,
			}
		)

	return results


def _ensure_learner_in_batch(batch: str, member: str):
	if not batch or not member:
		frappe.throw(_("Batch and member are required"))

	if not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found"))

	if not frappe.db.exists("User", member):
		frappe.throw(_("Learner not found"))

	if not frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": member}):
		frappe.throw(_("Learner is not enrolled in this batch"))


def _ensure_assessment_on_batch(batch: str, assessment_type: str, assessment_name: str):
	config = _get_assessment_reset_config(assessment_type)
	if not config:
		frappe.throw(_("Unsupported assessment type."))

	if not frappe.db.exists(config["doctype"], assessment_name):
		frappe.throw(_("{0} not found").format(config["label"]))

	if not frappe.db.exists(
		"LMS Assessment",
		{
			"parent": batch,
			"parenttype": "LMS Batch",
			"assessment_type": assessment_type,
			"assessment_name": assessment_name,
		},
	):
		frappe.throw(_("This assessment is not part of this batch."))


def _get_assessment_reset_config(assessment_type: str):
	configs = {
		"LMS Quiz": {
			"doctype": "LMS Quiz",
			"submission_doctype": "LMS Quiz Submission",
			"link_field": "quiz",
			"label": _("Quiz"),
			"no_attempts_msg": _("This learner has no quiz attempts to reset."),
		},
		"LMS Assignment": {
			"doctype": "LMS Assignment",
			"submission_doctype": "LMS Assignment Submission",
			"link_field": "assignment",
			"label": _("Assignment"),
			"no_attempts_msg": _("This learner has no assignment submissions to reset."),
		},
		"LMS Programming Exercise": {
			"doctype": "LMS Programming Exercise",
			"submission_doctype": "LMS Programming Exercise Submission",
			"link_field": "exercise",
			"label": _("Programming exercise"),
			"no_attempts_msg": _("This learner has no programming exercise attempts to reset."),
		},
	}
	return configs.get(assessment_type)


def _delete_learner_assessment_submissions(member: str, assessment_type: str, assessment_name: str) -> int:
	config = _get_assessment_reset_config(assessment_type)
	submissions = frappe.get_all(
		config["submission_doctype"],
		filters={config["link_field"]: assessment_name, "member": member},
		pluck="name",
	)

	if not submissions:
		frappe.throw(config["no_attempts_msg"])

	for submission in submissions:
		frappe.delete_doc(config["submission_doctype"], submission, ignore_permissions=True)

	return len(submissions)


@frappe.whitelist()
def reset_learner_assessment_attempt(
	batch: str, member: str, assessment_type: str, assessment_name: str
):
	"""Delete a learner's assessment submissions so they can attempt again."""
	_ensure_analytics_access()
	_ensure_learner_in_batch(batch, member)
	_ensure_assessment_on_batch(batch, assessment_type, assessment_name)

	config = _get_assessment_reset_config(assessment_type)
	deleted = _delete_learner_assessment_submissions(member, assessment_type, assessment_name)
	title = frappe.db.get_value(config["doctype"], assessment_name, "title") or assessment_name

	return {
		"deleted": deleted,
		"assessment_type": assessment_type,
		"assessment_name": assessment_name,
		"assessment_title": title,
		"member": member,
		"batch": batch,
	}


@frappe.whitelist()
def reset_learner_quiz_attempt(batch: str, member: str, quiz: str):
	"""Delete a learner's quiz submissions so they can retake the quiz."""
	return reset_learner_assessment_attempt(batch, member, "LMS Quiz", quiz)


@frappe.whitelist()
def get_analytics_learner_detail(batch: str, member: str):
	"""Detailed learner view for analytics instructor popup."""
	_ensure_analytics_access()

	_ensure_learner_in_batch(batch, member)

	user = frappe.db.get_value(
		"User",
		member,
		["full_name", "user_image", "username", "email", "last_active"],
		as_dict=True,
	)

	courses = frappe.get_all("Batch Course", filters={"parent": batch}, pluck="course")
	total_lessons = 0
	for course in courses:
		try:
			total_lessons += cint(get_lessons(course, get_details=False) or 0)
		except Exception:
			continue

	completed_lessons = 0
	for course in courses:
		completed_lessons += frappe.db.count(
			"LMS Course Progress",
			{"course": course, "member": member, "status": "Complete"},
		)

	review_name = frappe.db.get_value("LMS Learner Review", {"batch": batch, "member": member})
	review = frappe.get_doc("LMS Learner Review", review_name) if review_name else None

	mock_rating = review.mock_rating if review and review.mock_rating is not None else _default_mock_rating(
		member, batch
	)

	mock_result = None
	if review and review.mock_result:
		mock_result = {
			"file_url": review.mock_result,
			"file_name": review.mock_file_name or review.mock_result.split("/")[-1],
		}

	from lms.lms.mock_assessment import format_mock_list_row

	mock_rows = frappe.get_all(
		"LMS Mock Assessment",
		filters={"batch": batch, "member": member},
		fields=[
			"name",
			"title",
			"status",
			"overall_rating",
			"assessment_score_percent",
			"modified",
			"published_on",
		],
		order_by="modified desc",
	)
	mock_assessments = [format_mock_list_row(frappe._dict(row)) for row in mock_rows]

	return {
		"batch": batch,
		"member": member,
		"full_name": user.full_name,
		"user_image": user.user_image,
		"username": user.username,
		"email": user.email,
		"lessons_completed": completed_lessons,
		"lessons_total": total_lessons,
		"last_active": _relative_last_active(user.last_active),
		"quiz_average": _learner_quiz_average(member, batch),
		"mock_rating": mock_rating,
		"instructor_notes": review.instructor_notes if review else "",
		"review_name": review.name if review else None,
		"mock_result": mock_result,
		"mock_assessments": mock_assessments,
		"assessments": _learner_assessment_results(member, batch),
	}


@frappe.whitelist()
def save_analytics_learner_review(
	batch: str,
	member: str,
	instructor_notes: str = None,
	mock_rating: float = None,
	mock_result: str = None,
	mock_file_name: str = None,
):
	"""Save instructor-only learner review fields."""
	_ensure_analytics_access()

	if not batch or not member:
		frappe.throw(_("Batch and member are required"))

	doc = _get_or_create_learner_review(batch, member)

	if instructor_notes is not None:
		doc.instructor_notes = instructor_notes

	if mock_rating is not None and mock_rating != "":
		doc.mock_rating = flt(mock_rating)

	if mock_result:
		doc.mock_result = mock_result
		doc.mock_file_name = mock_file_name or mock_result.split("/")[-1]

	doc.save(ignore_permissions=True)
	return {"name": doc.name, "saved": True}


@frappe.whitelist()
def get_analytics_lesson_feedback(course: str = None):
	"""Lesson feedback satisfaction bars for a course."""
	_ensure_analytics_access()

	if _is_all_filter(course):
		course_names = _get_all_course_names()
		feedback_rows = []

		for course_name in course_names:
			course_title = frappe.db.get_value("LMS Course", course_name, "title") or course_name
			lessons = _get_course_lessons_ordered(course_name)

			for lesson in lessons:
				lesson_name = lesson.get("name") if isinstance(lesson, dict) else lesson.name
				lesson_title = lesson.get("title") if isinstance(lesson, dict) else lesson.title
				lesson_label = lesson.get("label") if isinstance(lesson, dict) else lesson.label

				yes_count = frappe.db.count(
					"LMS Lesson Feedback",
					{"lesson": lesson_name, "reaction": "Yes"},
				)
				no_count = frappe.db.count(
					"LMS Lesson Feedback",
					{"lesson": lesson_name, "reaction": "No"},
				)
				total = yes_count + no_count
				satisfaction = cint((yes_count / total) * 100) if total else 0
				title = lesson_title
				if len(course_names) > 1:
					title = f"{lesson_title} ({course_title})"

				feedback_rows.append(
					{
						"lesson": lesson_name,
						"title": title,
						"label": lesson_label,
						"yes_count": yes_count,
						"no_count": no_count,
						"satisfaction": satisfaction,
					}
				)

		return {"course": "__all__", "lessons": feedback_rows}

	if not frappe.db.exists("LMS Course", course):
		frappe.throw(_("Course not found"))

	lessons = _get_course_lessons_ordered(course)
	feedback_rows = []

	for lesson in lessons:
		lesson_name = lesson.get("name") if isinstance(lesson, dict) else lesson.name
		lesson_title = lesson.get("title") if isinstance(lesson, dict) else lesson.title
		lesson_label = lesson.get("label") if isinstance(lesson, dict) else lesson.label

		yes_count = frappe.db.count(
			"LMS Lesson Feedback",
			{"lesson": lesson_name, "reaction": "Yes"},
		)
		no_count = frappe.db.count(
			"LMS Lesson Feedback",
			{"lesson": lesson_name, "reaction": "No"},
		)
		total = yes_count + no_count
		satisfaction = cint((yes_count / total) * 100) if total else 0

		feedback_rows.append(
			{
				"lesson": lesson_name,
				"title": lesson_title,
				"label": lesson_label,
				"yes_count": yes_count,
				"no_count": no_count,
				"satisfaction": satisfaction,
			}
		)

	return {"course": course, "lessons": feedback_rows}


def get_file_info(file_url):
	"""Get file info for the given file URL."""
	file_info = frappe.db.get_value(
		"File", {"file_url": file_url}, ["file_name", "file_size", "file_url"], as_dict=1
	)
	return file_info


@frappe.whitelist(allow_guest=True)
def get_branding():
	"""Get branding details."""
	fields = ["app_name"]
	image_fields = ["banner_image", "footer_logo", "favicon", "app_logo"]
	fields = fields + image_fields
	settings = frappe._dict()

	for field in fields:
		value = frappe.get_cached_value("Website Settings", None, field)
		if field in image_fields and value:
			file_info = get_file_info(value)
			settings.update({field: json.loads(json.dumps(file_info))})
		else:
			settings.update({field: value})

	return settings


@frappe.whitelist()
def get_unsplash_photos(keyword: str = None):
	from lms.unsplash import get_by_keyword, get_list

	roles = set(frappe.get_roles())
	if roles.isdisjoint({"System Manager", "Moderator", "Course Creator"}):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def get_evaluator_details(evaluator: str):
	frappe.only_for("Batch Evaluator")

	if not frappe.db.exists("Google Calendar", {"user": evaluator}):
		calendar = frappe.new_doc("Google Calendar")
		calendar.update({"user": evaluator, "calendar_name": evaluator})
		calendar.insert()
	else:
		calendar = frappe.db.get_value(
			"Google Calendar", {"user": evaluator}, ["name", "authorization_code"], as_dict=1
		)

	if frappe.db.exists("Course Evaluator", {"evaluator": evaluator}):
		doc = frappe.get_doc("Course Evaluator", evaluator)
	else:
		doc = frappe.new_doc("Course Evaluator")
		doc.evaluator = evaluator
		doc.insert()
	return {
		"slots": doc.as_dict(),
		"calendar": calendar.name,
		"is_authorised": calendar.authorization_code,
	}


@frappe.whitelist()
def get_certified_participants(filters: dict = None, start: int = 0, page_length: int = 40):
	query = get_certification_query(filters)
	query = query.orderby("issue_date", order=frappe.qb.desc).offset(start).limit(page_length)
	participants = query.run(as_dict=True)
	for participant in participants:
		details = get_certified_participant_details(participant.member)
		participant.update(details)

	return participants


def get_certified_participant_details(member: str):
	count = frappe.db.count("LMS Certificate", {"member": member})
	details = frappe.db.get_value(
		"User",
		member,
		["full_name", "user_image", "username", "creation", "headline", "open_to"],
		as_dict=1,
	)
	details["certificate_count"] = count
	return details


def get_certification_query(filters: dict = None):
	Certificate = frappe.qb.DocType("LMS Certificate")
	User = frappe.qb.DocType("User")

	query = (
		frappe.qb.from_(Certificate)
		.select(Certificate.member, fn.Max(Certificate.issue_date).as_("issue_date"))
		.join(User)
		.on(Certificate.member == User.name)
		.where(Certificate.published == 1)
		.where(User.enabled == 1)
		.groupby(Certificate.member)
	)

	if filters:
		for field, value in filters.items():
			if field == "category":
				query = query.where(
					Certificate.course_title.like(f"%{value}%") | Certificate.batch_title.like(f"%{value}%")
				)
			if field == "member_name":
				query = query.where(Certificate.member_name.like(value[1]))
			if field == "open_to_work":
				query = query.where(User.open_to == "Work")
			if field == "hiring":
				query = query.where(User.open_to == "Hiring")
	return query


@frappe.whitelist()
def get_count_of_certified_members(filters: dict = None):
	query = get_certification_query(filters)
	result = query.run(as_dict=True)
	return len(result) or 0


@frappe.whitelist()
def get_certification_categories():
	categories = []
	seen = set()
	docs = frappe.get_all(
		"LMS Certificate",
		filters={
			"published": 1,
		},
		fields=["course_title", "batch_title"],
	)

	for doc in docs:
		category = doc.course_title if doc.course_title else doc.batch_title
		if not category or category in seen:
			continue

		seen.add(category)
		categories.append({"label": category, "value": category})
	return categories


@frappe.whitelist()
def get_all_users():
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	users = frappe.get_all(
		"User",
		{
			"enabled": 1,
		},
		["name", "full_name", "user_image"],
	)

	return {user.name: user for user in users}


@frappe.whitelist(allow_guest=True)
def get_sidebar_settings():
	lms_settings = frappe.get_single("LMS Settings")
	if frappe.session.user == "Guest" and not lms_settings.allow_guest_access:
		return []

	sidebar_items = frappe._dict()
	items = [
		"courses",
		"batches",
		"certifications",
		"jobs",
		"notifications",
		"programming_exercises",
	]
	for item in items:
		sidebar_items[item] = lms_settings.get(item)

	sidebar_items["analytics_dashboard"] = lms_settings.get("statistics")

	sidebar_items["analytics_dashboard"] = lms_settings.get("statistics")

	if len(lms_settings.sidebar_items):
		web_pages = frappe.get_all(
			"LMS Sidebar Item",
			{"parenttype": "LMS Settings", "parentfield": "sidebar_items"},
			["web_page", "route", "title as label", "icon", "name"],
		)
		for page in web_pages:
			page.to = page.route

		sidebar_items.web_pages = web_pages

	return sidebar_items


@frappe.whitelist()
def update_sidebar_item(webpage: str, icon: str):
	frappe.only_for("Moderator")
	filters = {
		"web_page": webpage,
		"parenttype": "LMS Settings",
		"parentfield": "sidebar_items",
		"parent": "LMS Settings",
	}

	if frappe.db.exists("LMS Sidebar Item", filters):
		frappe.db.set_value("LMS Sidebar Item", filters, "icon", icon)
	else:
		doc = frappe.new_doc("LMS Sidebar Item")
		doc.update(filters)
		doc.icon = icon
		doc.insert()


@frappe.whitelist()
def delete_sidebar_item(webpage: str):
	frappe.only_for("Moderator")
	return frappe.db.delete(
		"LMS Sidebar Item",
		{
			"web_page": webpage,
			"parenttype": "LMS Settings",
			"parentfield": "sidebar_items",
			"parent": "LMS Settings",
		},
	)


@frappe.whitelist()
def delete_lesson(lesson: str, chapter: str):
	course = frappe.db.get_value("Course Chapter", chapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this lesson."), frappe.PermissionError)

	lessons = frappe.get_all(
		"Lesson Reference",
		{"parent": chapter},
		pluck="lesson",
		order_by="idx",
	)
	lessons.remove(lesson)
	frappe.db.delete("Lesson Reference", {"parent": chapter, "lesson": lesson})
	update_index(lessons, chapter)

	frappe.db.delete("LMS Course Progress", {"lesson": lesson})
	frappe.delete_doc("Course Lesson", lesson)


@frappe.whitelist()
def update_lesson_index(lesson: str, sourceChapter: str, targetChapter: str, idx: int):
	course = frappe.db.get_value("Course Chapter", sourceChapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this lesson."), frappe.PermissionError)

	hasMoved = sourceChapter == targetChapter
	update_source_chapter(lesson, sourceChapter, idx, hasMoved)
	if not hasMoved:
		update_target_chapter(lesson, targetChapter, idx)


def update_source_chapter(lesson: str, chapter: str, idx: int, hasMoved: bool = False):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.remove(lesson)
	if not hasMoved:
		frappe.db.delete("Lesson Reference", {"parent": chapter, "lesson": lesson})
	else:
		lessons.insert(idx, lesson)

	update_index(lessons, chapter)


def update_target_chapter(lesson: str, chapter: str, idx: int):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.insert(idx, lesson)
	new_lesson_reference = frappe.new_doc("Lesson Reference")
	new_lesson_reference.update(
		{
			"lesson": lesson,
			"parent": chapter,
			"parenttype": "Course Chapter",
			"parentfield": "lessons",
		}
	)
	new_lesson_reference.insert()
	update_index(lessons, chapter)


def update_index(lessons: list, chapter: str):
	for row in lessons:
		frappe.db.set_value(
			"Lesson Reference", {"lesson": row, "parent": chapter}, "idx", lessons.index(row) + 1
		)


@frappe.whitelist()
def update_chapter_index(chapter: str, course: str, idx: int):
	"""Update the index of a chapter within a course"""

	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this chapter."), frappe.PermissionError)

	chapters = frappe.get_all(
		"Chapter Reference",
		{"parent": course},
		pluck="chapter",
		order_by="idx",
	)

	if chapter in chapters:
		chapters.remove(chapter)

	chapters.insert(idx, chapter)

	for i, chapter_name in enumerate(chapters):
		frappe.db.set_value("Chapter Reference", {"chapter": chapter_name, "parent": course}, "idx", i + 1)


@frappe.whitelist()
def get_members(start: int = 0, search: str = None):
	frappe.only_for(["Moderator"])
	filters = {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}
	or_filters = {}

	if search:
		or_filters["full_name"] = ["like", f"%{search}%"]
		or_filters["email"] = ["like", f"%{search}%"]

	members = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "user_image", "username", "last_active"],
		or_filters=or_filters,
		page_length=20,
		start=start,
	)

	for member in members:
		roles = frappe.get_all(
			"Has Role",
			{
				"parent": member.name,
				"parenttype": "User",
			},
			pluck="role",
		)
		if "Moderator" in roles:
			member.role = "Moderator"
		elif "Course Creator" in roles:
			member.role = "Course Creator"
		elif "Batch Evaluator" in roles:
			member.role = "Batch Evaluator"
		elif "LMS Student" in roles:
			member.role = "LMS Student"

	return members


def check_app_permission():
	"""Check if the user has permission to access the app."""
	if frappe.session.user == "Administrator":
		return True

	return has_lms_role()


@frappe.whitelist()
def save_evaluation_details(
	member: str,
	course: str,
	date_value: str,
	start_time: str,
	end_time: str,
	status: str,
	batch_name: str = None,
	evaluator: str = None,
	rating: float = 0,
	summary: str = None,
):
	"""
	Save evaluation details for a member against a course.
	"""
	frappe.only_for(["Batch Evaluator", "Moderator"])
	evaluation = frappe.db.exists("LMS Certificate Evaluation", {"member": member, "course": course})

	details = {
		"date": date_value,
		"start_time": start_time,
		"end_time": end_time,
		"status": status,
		"rating": rating / 5,
		"summary": summary,
		"batch_name": batch_name,
	}

	if evaluation:
		frappe.db.set_value("LMS Certificate Evaluation", evaluation, details)
		return evaluation
	else:
		doc = frappe.new_doc("LMS Certificate Evaluation")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def save_certificate_details(
	member: str,
	issue_date: str,
	template: str,
	course: str = None,
	batch_name: str = None,
	evaluator: str = None,
	expiry_date: str = None,
	published: bool = True,
):
	"""
	Save certificate details for a member against a course.
	"""
	frappe.only_for(["Batch Evaluator", "Moderator"])
	certificate = frappe.db.exists("LMS Certificate", {"member": member, "course": course})

	details = {
		"published": published,
		"issue_date": issue_date,
		"expiry_date": expiry_date,
		"template": template,
		"batch_name": batch_name,
	}

	if certificate:
		frappe.db.set_value("LMS Certificate", certificate, details)
		return certificate
	else:
		doc = frappe.new_doc("LMS Certificate")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def delete_documents(doctype: str, documents: list):
	frappe.only_for("Moderator")
	meta = frappe.get_meta(doctype)
	non_lms_allowed = ["Payment Gateway", "Email Template"]
	if meta.module != "LMS" and doctype not in non_lms_allowed:
		frappe.throw(_("Deletion not allowed for {0}").format(doctype))
	for doc in documents:
		if not isinstance(doc, str) or not doc.strip():
			frappe.throw(_("Invalid document name"))
		frappe.delete_doc(doctype, doc)


@frappe.whitelist()
def get_payment_gateway_details(payment_gateway: str):
	frappe.only_for("Moderator")
	gateway = frappe.get_doc("Payment Gateway", payment_gateway)

	if gateway.gateway_controller is None:
		try:
			data = frappe.get_doc(f"{payment_gateway} Settings").as_dict()
			meta = frappe.get_meta(f"{payment_gateway} Settings").fields
			doctype = f"{payment_gateway} Settings"
			docname = f"{payment_gateway} Settings"
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))
	else:
		try:
			data = frappe.get_doc(gateway.gateway_settings, gateway.gateway_controller).as_dict()
			meta = frappe.get_meta(gateway.gateway_settings).fields
			doctype = gateway.gateway_settings
			docname = gateway.gateway_controller
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))

	gateway_fields = get_transformed_fields(meta, data)

	return {
		"fields": gateway_fields,
		"data": data,
		"doctype": doctype,
		"docname": docname,
	}


def get_transformed_fields(meta: list, data: dict = None):
	transformed_fields = []
	for row in meta:
		if row.fieldtype not in ["Column Break", "Section Break"]:
			if row.fieldtype in ["Attach", "Attach Image"]:
				fieldtype = "Upload"
				if data and data.get(row.fieldname):
					data[row.fieldname] = get_file_info(data.get(row.fieldname))
			elif row.fieldtype == "Check":
				fieldtype = "checkbox"
			else:
				fieldtype = row.fieldtype

			field = {
				"label": row.label,
				"name": row.fieldname,
				"type": fieldtype,
			}

			if row.reqd:
				field["reqd"] = 1

			if row.options:
				field["options"] = row.options

			if row.default:
				field["default"] = row.default

			if row.description:
				field["description"] = row.description

			transformed_fields.append(field)

	return transformed_fields


@frappe.whitelist()
def get_new_gateway_fields(doctype: str):
	frappe.only_for("Moderator")
	try:
		meta = frappe.get_meta(doctype).fields
	except Exception:
		frappe.throw(_("{0} not found").format(doctype))

	transformed_fields = get_transformed_fields(meta)

	return transformed_fields


@frappe.whitelist()
def get_announcements(batch: str):
	roles = frappe.get_roles()
	is_batch_student = frappe.db.exists(
		"LMS Batch Enrollment", {"batch": batch, "member": frappe.session.user}
	)
	is_admin = "Moderator" in roles or "Batch Evaluator" in roles

	if not (is_batch_student or is_admin):
		frappe.throw(
			_("You do not have permission to access announcements for this batch."), frappe.PermissionError
		)

	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "LMS Batch",
			"reference_name": batch,
		},
		fields=[
			"subject",
			"content",
			"recipients",
			"cc",
			"communication_date",
			"sender",
			"sender_full_name",
		],
		order_by="communication_date desc",
	)

	for communication in communications:
		communication.image = frappe.get_cached_value("User", communication.sender, "user_image")

	return communications


@frappe.whitelist()
def delete_course(course: str):
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this course."), frappe.PermissionError)

	frappe.db.delete("LMS Enrollment", {"course": course})
	frappe.db.delete("LMS Course Progress", {"course": course})
	frappe.db.delete("LMS Certificate", {"course": course})
	frappe.db.delete("Batch Course", {"course": course})
	frappe.db.delete("LMS Course Review", {"course": course})
	from lms.lms.course_assessment_visibility import delete_visibility_for_course

	delete_visibility_for_course(course)
	frappe.db.delete("LMS Assessment", {"parent": course, "parenttype": "LMS Course"})
	frappe.db.set_value("LMS Quiz", {"course": course}, {"course": None, "lesson": None})
	frappe.db.set_value("LMS Quiz Submission", {"course": course}, "course", None)

	chapters = frappe.get_all("Course Chapter", {"course": course}, pluck="name")
	frappe.db.delete("Chapter Reference", {"parent": course})

	for chapter in chapters:
		lessons = frappe.get_all("Course Lesson", {"chapter": chapter}, pluck="name")

		frappe.db.delete("Lesson Reference", {"parent": chapter})

		for lesson in lessons:
			topics = frappe.get_all(
				"Discussion Topic",
				{"reference_doctype": "Course Lesson", "reference_docname": lesson},
				pluck="name",
			)

			for topic in topics:
				frappe.db.delete("Discussion Reply", {"topic": topic})
				frappe.db.delete("Discussion Topic", topic)

			frappe.delete_doc("Course Lesson", lesson)

	for chapter in chapters:
		frappe.delete_doc("Course Chapter", chapter)

	frappe.delete_doc("LMS Course", course)


@frappe.whitelist()
def set_course_assessment_visibility(course_assessment: str, batch: str, is_visible: int):
	course = frappe.db.get_value("LMS Assessment", course_assessment, "parent")
	if not course or not can_modify_course(course):
		frappe.throw(_("You are not authorized to change assessment visibility."))

	from lms.lms.course_assessment_visibility import set_visibility

	return set_visibility(course_assessment, batch, is_visible)


@frappe.whitelist()
def delete_course_assessment(course_assessment: str):
	course = frappe.db.get_value("LMS Assessment", course_assessment, "parent")
	if not course or not can_modify_course(course):
		frappe.throw(_("You are not authorized to remove this assessment."))

	from lms.lms.course_assessment_visibility import delete_visibility_for_assessment

	delete_visibility_for_assessment(course_assessment)
	frappe.delete_doc("LMS Assessment", course_assessment, ignore_permissions=True)


@frappe.whitelist()
def delete_batch(batch: str):
	if not can_modify_batch(batch):
		frappe.throw(_("You do not have permission to delete this batch."), frappe.PermissionError)

	frappe.db.delete("LMS Batch Enrollment", {"batch": batch})
	frappe.db.delete("Batch Course", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Assessment", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Timetable", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Feedback", {"batch": batch})
	delete_batch_discussions(batch)
	frappe.db.delete("LMS Batch", batch)


def delete_batch_discussions(batch: str):
	topics = frappe.get_all(
		"Discussion Topic",
		{"reference_doctype": "LMS Batch", "reference_docname": batch},
		pluck="name",
	)

	for topic in topics:
		frappe.db.delete("Discussion Reply", {"topic": topic})
		frappe.db.delete("Discussion Topic", topic)


def give_discussions_permission():
	doctypes = ["Discussion Topic", "Discussion Reply"]
	roles = ["LMS Student", "Course Creator", "Moderator", "Batch Evaluator"]
	for doctype in doctypes:
		for role in roles:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				frappe.get_doc(
					{
						"doctype": "Custom DocPerm",
						"parent": doctype,
						"role": role,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
						"if_owner": 0 if role == "Moderator" else 1,
					}
				).save()


@frappe.whitelist()
def upsert_chapter(
	title: str, course: str, is_scorm_package: bool, scorm_package: dict = None, name: str = None
):
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this chapter."), frappe.PermissionError)

	values = frappe._dict({"title": title, "course": course, "is_scorm_package": is_scorm_package})

	if is_scorm_package:
		scorm_package = frappe._dict(scorm_package)
		extract_path = extract_package(course, title, scorm_package)

		values.update(
			{
				"scorm_package": scorm_package.name,
				"scorm_package_path": extract_path.split("public")[1],
				"manifest_file": get_manifest_file(extract_path).split("public")[1],
				"launch_file": get_launch_file(extract_path).split("public")[1],
			}
		)

	if name:
		chapter = frappe.get_doc("Course Chapter", name)
	else:
		chapter = frappe.new_doc("Course Chapter")

	chapter.update(values)
	chapter.save()

	if is_scorm_package and not len(chapter.lessons):
		add_lesson(title, chapter.name, course, 1)

	return chapter


def extract_package(course: str, title: str, scorm_package: dict):
	package = frappe.get_doc("File", scorm_package.name)
	zip_path = package.get_full_path()
	scorm_root = os.path.realpath(frappe.get_site_path("public", "scorm"))
	extract_path = frappe.get_site_path("public", "scorm", course, title)

	if not os.path.realpath(extract_path).startswith(scorm_root + os.sep):
		frappe.throw(_("Invalid course or chapter name"))

	with zipfile.ZipFile(zip_path, "r") as zf:
		dest = os.path.realpath(extract_path)
		for name in zf.namelist():
			target = os.path.realpath(os.path.join(extract_path, name))
			if not target.startswith(dest + os.sep) and target != dest:
				frappe.throw(_("Invalid file path in package"))
		zf.extractall(extract_path)

	return extract_path


def check_for_malicious_code(zip_path):
	"""Scan SCORM packages for XXE / remote script injection only.

	SCORM 1.2/2004 packages (Rise, Articulate, etc.) routinely use inline
	handlers and Function/eval in bundled JS — those are not treated as malware.
	"""
	# High-confidence risks only (false positives block real course packages)
	dangerous_patterns = [
		r"<!ENTITY",  # XXE
		r'<script[^>]+src\s*=\s*["\']https?://',  # remote script load
	]

	with zipfile.ZipFile(zip_path, "r") as zf:
		for file_name in zf.namelist():
			lower = file_name.lower()
			if not lower.endswith((".html", ".htm", ".xml", ".js")):
				continue
			with zf.open(file_name) as file:
				content = file.read().decode("utf-8", errors="ignore")
				for pattern in dangerous_patterns:
					if re.search(pattern, content, flags=re.IGNORECASE):
						frappe.throw(
							_("Suspicious pattern found in {0}: {1}").format(file_name, pattern)
						)


def get_manifest_file(extract_path: str):
	manifest_file = None
	for root, _dirs, files in os.walk(extract_path):
		for file in files:
			if file == "imsmanifest.xml":
				manifest_file = os.path.join(root, file)
				break
		if manifest_file:
			break
	return manifest_file


def get_launch_file(extract_path: str):
	launch_file = None
	manifest_file = get_manifest_file(extract_path)

	if manifest_file:
		with open(manifest_file) as file:
			data = file.read()
			dom = parseString(data)
			resource = dom.getElementsByTagName("resource")
			for res in resource:
				if (
					res.getAttribute("adlcp:scormtype") == "sco"
					or res.getAttribute("adlcp:scormType") == "sco"
				):
					launch_file = res.getAttribute("href")
					break

		if launch_file:
			launch_file = os.path.join(os.path.dirname(manifest_file), launch_file)

	return launch_file


def add_lesson(title: str, chapter: str, course: str, idx: int):
	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
		}
	)
	lesson.insert()

	lesson_reference = frappe.new_doc("Lesson Reference")
	lesson_reference.update(
		{
			"lesson": lesson.name,
			"idx": idx,
			"parent": chapter,
			"parenttype": "Course Chapter",
			"parentfield": "lessons",
		}
	)
	lesson_reference.insert()


@frappe.whitelist()
def delete_chapter(chapter: str):
	course = frappe.db.get_value("Course Chapter", chapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this chapter."), frappe.PermissionError)

	chapterInfo = frappe.db.get_value(
		"Course Chapter", chapter, ["is_scorm_package", "scorm_package_path"], as_dict=True
	)

	if chapterInfo.is_scorm_package:
		delete_scorm_package(chapterInfo.scorm_package_path)

	course = frappe.db.get_value("Chapter Reference", {"chapter": chapter}, "parent")

	frappe.db.delete("Chapter Reference", {"chapter": chapter})
	frappe.db.delete("Lesson Reference", {"parent": chapter})
	frappe.db.delete("Course Lesson", {"chapter": chapter})
	frappe.db.delete("Course Chapter", chapter)

	# reset chapter reference index after deletion
	if course:
		chapters = frappe.get_all(
			"Chapter Reference", filters={"parent": course}, fields=["name"], order_by="idx asc"
		)

		i = 1
		for chapter in chapters:
			frappe.db.set_value("Chapter Reference", chapter.name, "idx", i)
			i += 1


def delete_scorm_package(scorm_package_path: str):
	scorm_package_path = frappe.get_site_path("public", scorm_package_path[1:])
	if os.path.exists(scorm_package_path):
		shutil.rmtree(scorm_package_path)


@frappe.whitelist()
def mark_lesson_progress(course: str, chapter_number: int, lesson_number: int):
	chapter_name = frappe.get_value("Chapter Reference", {"parent": course, "idx": chapter_number}, "chapter")
	lesson_name = frappe.get_value(
		"Lesson Reference", {"parent": chapter_name, "idx": lesson_number}, "lesson"
	)
	save_progress(lesson_name, course)


@frappe.whitelist()
def get_quiz_progress(lesson: str):
	"""Check if the current user has passed all quizzes in a lesson."""
	from lms.lms.doctype.course_lesson.course_lesson import get_quiz_progress as _get_quiz_progress
	return _get_quiz_progress(lesson)


@frappe.whitelist()
def complete_lesson(lesson: str, course: str):
	"""Mark a lesson complete and return the next unlocked lesson."""
	from lms.lms.doctype.course_lesson.course_lesson import (
		get_assignment_progress,
		get_next_lesson,
		get_quiz_progress,
	)
	from lms.lms.lesson_locking import (
		get_lesson_route_numbers,
		is_lesson_unlocked,
		should_enforce_sequential_locking,
	)
	from lms.lms.utils import get_course_progress, get_lesson_index

	membership = frappe.db.exists("LMS Enrollment", {"course": course, "member": frappe.session.user})
	if not membership:
		frappe.throw(_("You are not enrolled in this course."), frappe.PermissionError)

	if should_enforce_sequential_locking(course) and not is_lesson_unlocked(
		course, lesson, frappe.session.user
	):
		frappe.throw(_("This lesson is locked."), frappe.PermissionError)

	if not get_quiz_progress(lesson):
		frappe.throw(_("Please pass all quizzes before completing this lesson."))

	if not get_assignment_progress(lesson):
		frappe.throw(_("Please submit all assignments before completing this lesson."))

	if not frappe.db.exists(
		"LMS Course Progress",
		{"lesson": lesson, "member": frappe.session.user, "status": "Complete"},
	):
		frappe.get_doc(
			{
				"doctype": "LMS Course Progress",
				"lesson": lesson,
				"status": "Complete",
				"member": frappe.session.user,
			}
		).save(ignore_permissions=True)

	next_lesson = get_next_lesson(course, lesson)
	if next_lesson:
		frappe.db.set_value(
			"LMS Enrollment",
			membership,
			"current_lesson",
			next_lesson,
			update_modified=False,
		)

	progress = get_course_progress(course)
	enrollment = frappe.get_doc("LMS Enrollment", membership)
	enrollment.progress = progress
	enrollment.flags.ignore_version = True
	enrollment.flags.allow_progress_update = True
	enrollment.save()
	enrollment.run_method("on_change")

	next_route = None
	if next_lesson:
		numbers = get_lesson_route_numbers(next_lesson)
		next_route = {
			"lesson": next_lesson,
			"chapter_number": numbers["chapter_number"],
			"lesson_number": numbers["lesson_number"],
			"index": get_lesson_index(next_lesson),
		}

	return {"progress": progress, "next_lesson": next_route}


@frappe.whitelist()
def get_heatmap_data(member: str, base_days: int = 200):
	if not (has_course_instructor_role() or has_moderator_role() or has_evaluator_role()):
		frappe.throw(_("You do not have permission to access heatmap data."), frappe.PermissionError)

	base_date, start_date, number_of_days, days = calculate_date_ranges(base_days)
	date_count = initialize_date_count(days)

	lesson_completions, quiz_submissions, assignment_submissions = fetch_activity_data(member, start_date)
	count_dates(lesson_completions, date_count)
	count_dates(quiz_submissions, date_count)
	count_dates(assignment_submissions, date_count)

	heatmap_data, labels, total_activities, weeks = prepare_heatmap_data(
		start_date, number_of_days, date_count
	)

	return {
		"heatmap_data": heatmap_data,
		"labels": labels,
		"total_activities": total_activities,
		"weeks": weeks,
	}


def calculate_date_ranges(base_days: int):
	today = format_date(now(), "YYYY-MM-dd")
	day_today = get_datetime(today).strftime("%w")
	padding_end = 6 - cint(day_today)

	base_date = add_days(today, -base_days)
	day_of_base_date = cint(get_datetime(base_date).strftime("%w"))
	start_date = add_days(base_date, -day_of_base_date)
	number_of_days = base_days + day_of_base_date + padding_end
	days = [add_days(start_date, i) for i in range(number_of_days + 1)]

	return base_date, start_date, number_of_days, days


def initialize_date_count(days: list):
	return {format_date(day, "YYYY-MM-dd"): 0 for day in days}


def fetch_activity_data(member: str, start_date: str):
	lesson_completions = frappe.get_all(
		"LMS Course Progress",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date], "status": "Complete"},
	)

	quiz_submissions = frappe.get_all(
		"LMS Quiz Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	assignment_submissions = frappe.get_all(
		"LMS Assignment Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	return lesson_completions, quiz_submissions, assignment_submissions


def count_dates(data: list, date_count: dict):
	for entry in data:
		date_value = format_date(entry.creation, "YYYY-MM-dd")
		if date_value in date_count:
			date_count[date_value] += 1


def prepare_heatmap_data(start_date: str, number_of_days: int, date_count: dict):
	days_of_week = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
	heatmap_data = {day: [] for day in days_of_week}
	week_count = -(number_of_days // -7)
	labels = [None] * week_count
	last_seen_month = None
	sorted_dates = sorted(date_count.keys())

	for date_value in sorted_dates:
		activity_count = date_count[date_value]
		day_of_week = get_datetime(date_value).strftime("%a")
		current_month = get_datetime(date_value).strftime("%b")
		column_index = get_week_difference(start_date, date_value)

		if 0 <= column_index < week_count:
			heatmap_data[day_of_week].append(
				{
					"date": date_value,
					"count": activity_count,
					"label": f"{activity_count} activities on {format_date(date_value, 'dd MMM')}",
				}
			)

			if last_seen_month != current_month:
				labels[column_index] = current_month
				last_seen_month = current_month

	for index, label in enumerate(labels):
		if not label:
			labels[index] = ""

	formatted_heatmap_data = [{"name": day, "data": heatmap_data[day]} for day in days_of_week]

	total_activities = sum(date_count.values())
	return formatted_heatmap_data, labels, total_activities, week_count


def get_week_difference(start_date: str, current_date: str) -> int:
	diff_in_days = date_diff(current_date, start_date)
	return diff_in_days // 7


@frappe.whitelist()
def get_notifications(filters: dict = None):
	filters = frappe._dict(filters or {})
	filters.for_user = frappe.session.user
	notifications = frappe.get_all(
		"Notification Log",
		filters,
		[
			"subject",
			"from_user",
			"link",
			"read",
			"name",
			"creation",
			"document_type",
			"document_name",
			"type",
			"email_content",
		],
		order_by="creation desc",
	)

	for notification in notifications:
		notification = update_document_details(notification)
		notification = update_user_details(notification)

	return notifications


def update_user_details(notification: dict) -> dict:
	if (
		notification.document_details
		and len(notification.document_details.get("instructors", []))
		and not is_mention(notification)
	):
		from_user_details = notification.document_details["instructors"][0]
	else:
		from_user_details = frappe.db.get_value(
			"User", notification.from_user, ["full_name", "user_image"], as_dict=1
		)
	notification["from_user_details"] = from_user_details
	return notification


def is_mention(notification: dict) -> bool:
	if notification.type == "Mention":
		return True
	if "mentioned you" in notification.subject.lower():
		return True
	return False


def update_document_details(notification: dict) -> dict:
	if notification.document_type == "LMS Course":
		details = frappe.db.get_value(
			"LMS Course", notification.document_name, ["title", "video_link", "short_introduction"], as_dict=1
		)
		instructors = get_instructors("LMS Course", notification.document_name)
		details["instructors"] = instructors
		notification["document_details"] = details

	elif notification.document_type == "LMS Batch":
		details = frappe.db.get_value(
			"LMS Batch",
			notification.document_name,
			[
				"title",
				"description as short_introduction",
				"video_link",
				"start_date",
				"end_date",
				"start_time",
				"timezone",
			],
			as_dict=1,
		)
		instructors = get_instructors("LMS Batch", notification.document_name)
		details["instructors"] = instructors
		notification["document_details"] = details
	return notification


@frappe.whitelist(allow_guest=True)
def get_lms_settings():
	allowed_fields = [
		"allow_guest_access",
		"prevent_skipping_videos",
		"contact_us_email",
		"contact_us_url",
		"livecode_url",
		"disable_pwa",
		"allow_job_posting",
		"demo_data_present",
	]

	settings = frappe._dict()
	for field in allowed_fields:
		settings[field] = frappe.get_cached_value("LMS Settings", None, field)

	return settings


@frappe.whitelist()
def cancel_evaluation(evaluation: dict):
	evaluation = frappe._dict(evaluation)
	if evaluation.member != frappe.session.user:
		frappe.throw(_("You do not have permission to cancel this evaluation."), frappe.PermissionError)

	if not frappe.db.exists(
		"LMS Certificate Request",
		{
			"name": evaluation.name,
			"member": frappe.session.user,
		},
	):
		frappe.throw(_("You do not have permission to cancel this evaluation."), frappe.PermissionError)

	frappe.db.set_value("LMS Certificate Request", evaluation.name, "status", "Cancelled")
	events = frappe.get_all(
		"Event Participants",
		{
			"email": evaluation.member,
		},
		["parent", "name"],
	)

	for event in events:
		info = frappe.db.get_value("Event", event.parent, ["starts_on", "subject"], as_dict=1)
		date_value = str(info.starts_on).split(" ")[0]

		if date_value == str(evaluation.date.format("YYYY-MM-DD")) and evaluation.member_name in info.subject:
			communication = frappe.db.get_value(
				"Communication",
				{"reference_doctype": "Event", "reference_name": event.parent},
				"name",
			)
			if communication:
				frappe.delete_doc("Communication", communication, ignore_permissions=True)

			frappe.delete_doc("Event Participants", event.name, ignore_permissions=True)
			frappe.delete_doc("Event", event.parent, ignore_permissions=True)


@frappe.whitelist()
def get_certification_details(course: str):
	from lms.lms.doctype.lms_course_feedback.lms_course_feedback import (
		is_feedback_completed,
	)
	from lms.lms.utils import get_course_progress

	membership = None
	filters = {"course": course, "member": frappe.session.user}

	if frappe.db.exists("LMS Enrollment", filters):
		membership = frappe.db.get_value(
			"LMS Enrollment",
			filters,
			["name", "purchased_certificate", "progress", "feedback_completed"],
			as_dict=1,
		)

	paid_certificate = frappe.db.get_value("LMS Course", course, "paid_certificate")
	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": frappe.session.user, "course": course},
		["name", "template"],
		as_dict=1,
	)
	feedback_done = is_feedback_completed(course, frappe.session.user)
	progress = flt(get_course_progress(course, frappe.session.user) or 0) if membership else 0

	return {
		"membership": membership,
		"paid_certificate": paid_certificate,
		"certificate": certificate,
		"feedback_completed": feedback_done,
		"course_completed": progress >= 100,
		"can_generate_certificate": progress >= 100,
	}


@frappe.whitelist()
def save_role(user: str, role: str, value: int):
	frappe.only_for("Moderator")
	if role not in LMS_ROLES:
		frappe.throw(_("You do not have permission to modify this role."), frappe.PermissionError)

	if role == "Batch Evaluator":
		return save_evaluator_role(user, value)

	if cint(value):
		if not frappe.db.exists("Has Role", {"parent": user, "role": role}):
			doc = frappe.new_doc("Has Role")
			doc.parent = user
			doc.parenttype = "User"
			doc.parentfield = "roles"
			doc.role = role
			doc.save(ignore_permissions=True)
	else:
		frappe.db.delete("Has Role", {"parent": user, "role": role})
	frappe.clear_cache(user=user)
	return True


def save_evaluator_role(user: str, value: int):
	frappe.only_for("Moderator")
	if cint(value):
		if not frappe.db.exists("Has Role", {"parent": user, "role": "Batch Evaluator"}):
			doc = frappe.new_doc("Has Role")
			doc.parent = user
			doc.parenttype = "User"
			doc.parentfield = "roles"
			doc.role = "Batch Evaluator"
			doc.save(ignore_permissions=True)
		if not frappe.db.exists("Course Evaluator", {"evaluator": user}):
			doc = frappe.new_doc("Course Evaluator")
			doc.evaluator = user
			doc.save(ignore_permissions=True)
	else:
		frappe.db.delete("Has Role", {"parent": user, "role": "Batch Evaluator"})
		if frappe.db.exists("Course Evaluator", {"evaluator": user}):
			frappe.db.delete("Course Evaluator", {"evaluator": user})
	frappe.clear_cache(user=user)
	return True


@frappe.whitelist()
def capture_user_persona(responses: str):
	frappe.only_for("System Manager")
	data = frappe.parse_json(responses)
	data = json.dumps(data)
	response = frappe.integrations.utils.make_post_request(
		"https://school.frappe.io/api/method/capture-persona",
		data={"response": data},
	)
	if response.get("message").get("name"):
		frappe.db.set_single_value("LMS Settings", "persona_captured", True)
	return response


@frappe.whitelist()
def get_meta_info(type: str, route: str):
	if frappe.db.exists("Website Meta Tag", {"parent": f"{type}/{route}"}):
		meta_tags = frappe.get_all(
			"Website Meta Tag",
			{
				"parent": f"{type}/{route}",
			},
			["name", "key", "value"],
		)

		return meta_tags

	return []


@frappe.whitelist()
def update_meta_info(meta_type: str, route: str, meta_tags: list):
	frappe.only_for(["Course Creator", "Batch Evaluator", "Moderator"])
	validate_meta_data_permissions(meta_type)
	validate_meta_tags(meta_tags)

	parent_name = f"{meta_type}/{route}"
	for tag in meta_tags:
		existing_tag = frappe.db.exists(
			"Website Meta Tag",
			{
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
			},
		)
		if existing_tag:
			if not tag.get("value"):
				frappe.db.delete("Website Meta Tag", existing_tag)
				continue
			frappe.db.set_value("Website Meta Tag", existing_tag, "value", tag["value"])
		elif tag.get("value"):
			tag_properties = {
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
				"value": tag["value"],
			}

			parent_exists = frappe.db.exists("Website Route Meta", parent_name)
			if not parent_exists:
				create_meta(parent_name, tag_properties)
			else:
				create_meta_tag(tag_properties)


def validate_meta_tags(meta_tags: list):
	if not isinstance(meta_tags, list):
		frappe.throw(_("Meta tags should be a list."))
	for tag in meta_tags:
		if tag.get("value"):
			tag["value"] = frappe.utils.strip_html_tags(str(tag["value"]))


def create_meta(parent_name: str, tag_properties: dict):
	route_meta = frappe.new_doc("Website Route Meta")
	route_meta.update(
		{
			"__newname": parent_name,
		}
	)
	route_meta.append("meta_tags", tag_properties)
	route_meta.insert()


def create_meta_tag(tag_properties: dict):
	new_tag = frappe.new_doc("Website Meta Tag")
	new_tag.update(tag_properties)
	new_tag.insert()


def validate_meta_data_permissions(meta_type: str):
	roles = frappe.get_roles()

	if meta_type == "courses":
		if not ("Course Creator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))

	elif meta_type == "batches":
		if not ("Batch Evaluator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))


@frappe.whitelist()
def create_programming_exercise_submission(exercise: str, submission: str, code: str, test_cases: list):
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	if submission == "new":
		return make_new_exercise_submission(exercise, code, test_cases)
	else:
		update_exercise_submission(submission, code, test_cases)


def make_new_exercise_submission(exercise: str, code: str, test_cases: list):
	submission = frappe.new_doc("LMS Programming Exercise Submission")
	submission.exercise = exercise
	submission.member = frappe.session.user
	submission.code = code

	for test_case in test_cases:
		submission.append(
			"test_cases",
			{
				"input": test_case.get("input"),
				"output": test_case.get("output"),
				"expected_output": test_case.get("expected_output"),
				"status": test_case.get("status", test_case.get("status", "Failed")),
			},
		)

	submission.status = get_exercise_status(test_cases)
	submission.insert()
	return submission.name


def update_exercise_submission(submission: str, code: str, test_cases: list):
	member = frappe.db.get_value("LMS Programming Exercise Submission", submission, "member")
	if member != frappe.session.user:
		frappe.throw(_("You do not have permission to update this submission."), frappe.PermissionError)

	update_test_cases(test_cases, submission)
	status = get_exercise_status(test_cases)
	frappe.db.set_value("LMS Programming Exercise Submission", submission, {"status": status, "code": code})


def get_exercise_status(test_cases: list):
	if not test_cases:
		return "Failed"

	if all(row.get("status", "Failed") == "Passed" for row in test_cases):
		return "Passed"
	else:
		return "Failed"


def update_test_cases(test_cases: list, submission: str):
	frappe.db.delete("LMS Test Case Submission", {"parent": submission})
	for row in test_cases:
		test_case = frappe.new_doc("LMS Test Case Submission")
		test_case.update(
			{
				"parent": submission,
				"parenttype": "LMS Programming Exercise Submission",
				"parentfield": "test_cases",
				"input": row.get("input"),
				"output": row.get("output"),
				"expected_output": row.get("expected_output"),
				"status": row.get("status", "Failed"),
			}
		)
		test_case.insert()


@frappe.whitelist()
def track_video_watch_duration(lesson: str, videos: list):
	"""
	Track the watch duration of videos in a lesson.
	"""
	if not isinstance(videos, list):
		videos = json.loads(videos)

	for video in videos:
		filters = {
			"lesson": lesson,
			"source": video.get("source"),
			"member": frappe.session.user,
		}
		existing_record = frappe.db.get_value(
			"LMS Video Watch Duration", filters, ["name", "watch_time"], as_dict=True
		)
		if existing_record and flt(existing_record.watch_time) < flt(video.get("watch_time")):
			frappe.db.set_value(
				"LMS Video Watch Duration",
				filters,
				"watch_time",
				video.get("watch_time"),
			)
		elif not existing_record:
			track_new_watch_time(lesson, video)


def track_new_watch_time(lesson: str, video: dict):
	doc = frappe.new_doc("LMS Video Watch Duration")
	doc.lesson = lesson
	doc.source = video.get("source")
	doc.watch_time = video.get("watch_time")
	doc.member = frappe.session.user
	doc.save()


@frappe.whitelist()
def get_course_progress_distribution(course: str):
	if not can_modify_course(course):
		frappe.throw(
			_("You do not have permission to access this course's progress data."), frappe.PermissionError
		)

	all_progress = frappe.get_all(
		"LMS Enrollment",
		{
			"course": course,
		},
		pluck="progress",
	)

	average_progress = get_average_course_progress(all_progress)
	progress_distribution = get_progress_distribution(all_progress)

	return {
		"average_progress": average_progress,
		"progress_distribution": progress_distribution,
	}


def get_average_course_progress(progress_list: list):
	if not progress_list:
		return 0
	average_progress = sum(progress_list) / len(progress_list)
	return flt(average_progress, frappe.get_system_settings("float_precision") or 3)


def get_progress_distribution(progressList: list):
	distribution = [
		{
			"name": "Just Started (0-30%)",
			"value": len([p for p in progressList if 0 <= p < 30]),
		},
		{
			"name": "In Progress (30-60%)",
			"value": len([p for p in progressList if 30 <= p < 60]),
		},
		{
			"name": "Advanced (60-99%)",
			"value": len([p for p in progressList if 60 <= p < 100]),
		},
		{
			"name": "Completed (100%)",
			"value": len([p for p in progressList if p == 100]),
		},
	]

	return distribution


@frappe.whitelist(allow_guest=True)
def get_pwa_manifest():
	title = frappe.db.get_single_value("Website Settings", "app_name") or "Frappe Learning"
	banner_image = frappe.db.get_single_value("Website Settings", "banner_image")

	manifest = {
		"name": title,
		"short_name": title,
		"description": "Easy to use, 100% open source Learning Management System",
		"start_url": get_lms_route(),
		"icons": [
			{
				"src": banner_image or "/assets/lms/frontend/manifest/manifest-icon-192.maskable.png",
				"sizes": "192x192",
				"type": "image/png",
				"purpose": "maskable any",
			}
		],
	}

	return Response(json.dumps(manifest), status=200, content_type="application/manifest+json")


@frappe.whitelist()
def get_profile_details(username: str):
	details = frappe.db.get_value(
		"User",
		{"username": username},
		[
			"first_name",
			"last_name",
			"full_name",
			"name",
			"username",
			"user_image",
			"bio",
			"headline",
			"language",
			"cover_image",
			"open_to",
			"linkedin",
			"github",
			"twitter",
		],
		as_dict=True,
	)
	roles = frappe.get_roles(details.name)
	if not has_lms_role():
		frappe.throw(
			_("User does not have permission to access this user's profile details."), frappe.PermissionError
		)
	details.roles = roles
	return details


@frappe.whitelist()
def get_streak_info():
	all_dates = fetch_activity_dates(frappe.session.user)
	streak, longest_streak = calculate_streaks(all_dates)
	current_streak = calculate_current_streak(all_dates, streak)

	return {
		"current_streak": current_streak,
		"longest_streak": longest_streak,
	}


def fetch_activity_dates(user: str):
	doctypes = [
		"LMS Course Progress",
		"LMS Quiz Submission",
		"LMS Assignment Submission",
		"LMS Programming Exercise Submission",
	]

	all_dates = []
	for dt in doctypes:
		all_dates.extend(frappe.get_all(dt, {"member": user}, pluck="creation"))

	return sorted({d.date() if hasattr(d, "date") else d for d in all_dates})


def calculate_streaks(all_dates: list):
	streak = 0
	longest_streak = 0
	prev_day = None

	for d in all_dates:
		if d.weekday() in (5, 6):
			continue

		if prev_day:
			expected = prev_day + timedelta(days=1)
			while expected.weekday() in (5, 6):
				expected += timedelta(days=1)

			streak = streak + 1 if d == expected else 1
		else:
			streak = 1

		longest_streak = max(longest_streak, streak)
		prev_day = d

	return streak, longest_streak


def calculate_current_streak(all_dates: list, streak: int):
	if not all_dates:
		return 0

	last_date = all_dates[-1]
	today = getdate()

	ref_day = today
	while ref_day.weekday() in (5, 6):
		ref_day -= timedelta(days=1)

	if last_date == ref_day or last_date == ref_day - timedelta(days=1):
		return streak
	return 0


@frappe.whitelist()
def get_my_live_classes():
	my_live_classes = []

	batches = frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		pluck="batch",
	)

	live_class_details = frappe.get_all(
		"LMS Live Class",
		filters={
			"date": [">=", getdate()],
			"batch_name": ["in", batches],
		},
		fields=[
			"name",
			"title",
			"description",
			"time",
			"date",
			"duration",
			"attendees",
			"start_url",
			"join_url",
			"owner",
		],
		limit=2,
		order_by="date",
	)

	if len(live_class_details):
		for live_class in live_class_details:
			live_class.course_title = frappe.db.get_value("LMS Course", live_class.course, "title")

			my_live_classes.append(live_class)

	return my_live_classes


@frappe.whitelist()
def get_created_courses():
	created_courses = []
	roles = frappe.get_roles()

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Course = frappe.qb.DocType("LMS Course")

	base_query = (
		frappe.qb.from_(CourseInstructor)
		.join(Course)
		.on(CourseInstructor.parent == Course.name)
		.select(Course.name)
		.orderby(Course.published_on, order=frappe.qb.desc)
		.limit(3)
	)

	query = base_query.where(CourseInstructor.instructor == frappe.session.user)
	results = query.run(as_dict=True)

	if not len(results) and ("Moderator" in roles):
		results = base_query.run(as_dict=True)

	courses = [row["name"] for row in results]
	for course in courses:
		course_details = get_course_details(course)
		created_courses.append(course_details)

	return created_courses


@frappe.whitelist()
def get_created_batches():
	created_batches = []

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Batch = frappe.qb.DocType("LMS Batch")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(Batch)
		.on(CourseInstructor.parent == Batch.name)
		.select(Batch.name)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(Batch.start_date >= getdate())
		.orderby(Batch.start_date, order=frappe.qb.asc)
		.limit(4)
	)

	results = query.run(as_dict=True)
	batches = [row["name"] for row in results]

	for batch in batches:
		batch_details = get_batch_details(batch)
		created_batches.append(batch_details)

	return created_batches


@frappe.whitelist()
def get_admin_live_classes():
	CourseInstructor = frappe.qb.DocType("Course Instructor")
	LMSLiveClass = frappe.qb.DocType("LMS Live Class")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(LMSLiveClass)
		.on(CourseInstructor.parent == LMSLiveClass.batch_name)
		.select(
			LMSLiveClass.name,
			LMSLiveClass.title,
			LMSLiveClass.description,
			LMSLiveClass.time,
			LMSLiveClass.date,
			LMSLiveClass.duration,
			LMSLiveClass.attendees,
			LMSLiveClass.start_url,
			LMSLiveClass.join_url,
			LMSLiveClass.owner,
		)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(LMSLiveClass.date >= getdate())
		.orderby(LMSLiveClass.date, order=frappe.qb.asc)
		.limit(4)
	)
	results = query.run(as_dict=True)
	return results


@frappe.whitelist()
def get_admin_evals():
	evals = frappe.get_all(
		"LMS Certificate Request",
		{
			"evaluator": frappe.session.user,
			"date": [">=", getdate()],
			"status": "Upcoming",
		},
		[
			"name",
			"date",
			"start_time",
			"course",
			"evaluator",
			"google_meet_link",
			"member",
			"member_name",
		],
		limit=4,
		order_by="date asc",
	)

	for evaluation in evals:
		evaluation.course_title = frappe.db.get_value("LMS Course", evaluation.course, "title")

	return evals


@frappe.whitelist()
def get_my_courses():
	my_courses = []
	courses = get_my_latest_courses()

	if not len(courses):
		courses = get_featured_home_courses()

	if not len(courses):
		courses = get_popular_courses()

	for course in courses:
		my_courses.append(get_course_details(course))

	return my_courses


def get_my_latest_courses():
	return frappe.get_all(
		"LMS Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="modified desc",
		limit=3,
		pluck="course",
	)


def get_featured_home_courses():
	return frappe.get_all(
		"LMS Course",
		{"published": 1, "featured": 1},
		order_by="published_on desc",
		limit=3,
		pluck="name",
	)


def get_popular_courses():
	return frappe.get_all(
		"LMS Course",
		{
			"published": 1,
		},
		order_by="enrollments desc",
		limit=3,
		pluck="name",
	)


@frappe.whitelist()
def get_my_batches():
	my_batches = []
	batches = get_my_latest_batches()

	if not len(batches):
		batches = get_upcoming_batches()

	for batch in batches:
		batch_details = get_batch_details(batch)
		if batch_details:
			my_batches.append(batch_details)

	return my_batches


def get_my_latest_batches():
	return frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		limit=4,
		pluck="batch",
	)


def get_upcoming_batches():
	return frappe.get_all(
		"LMS Batch",
		{
			"published": 1,
			"start_date": [">=", getdate()],
		},
		order_by="start_date asc",
		limit=4,
		pluck="name",
	)


@frappe.whitelist()
def delete_programming_exercise(exercise: str):
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	frappe.db.delete("LMS Programming Exercise Submission", {"exercise": exercise})
	frappe.db.delete("LMS Programming Exercise", exercise)


@frappe.whitelist()
def get_lesson_completion_stats(course: str):
	roles = frappe.get_roles()
	if "Course Creator" not in roles and "Moderator" not in roles:
		frappe.throw(_("You do not have permission to access lesson completion stats."))

	CourseProgress = frappe.qb.DocType("LMS Course Progress")
	LessonReference = frappe.qb.DocType("Lesson Reference")
	ChapterReference = frappe.qb.DocType("Chapter Reference")
	Lesson = frappe.qb.DocType("Course Lesson")

	rows = (
		frappe.qb.from_(LessonReference)
		.join(ChapterReference)
		.on(LessonReference.parent == ChapterReference.chapter)
		.join(Lesson)
		.on(LessonReference.lesson == Lesson.name)
		.left_join(CourseProgress)
		.on(
			(CourseProgress.lesson == LessonReference.lesson)
			& (CourseProgress.course == course)
			& (CourseProgress.status == "Complete")
		)
		.select(
			LessonReference.idx,
			ChapterReference.idx.as_("chapter_idx"),
			CourseProgress.lesson,
			Lesson.title,
			Lesson.name.as_("lesson_name"),
			fn.Count(CourseProgress.name).as_("completion_count"),
		)
		.where(ChapterReference.parent == course)
		.groupby(LessonReference.lesson)
		.orderby(ChapterReference.idx, LessonReference.idx)
		.run(as_dict=True)
	)

	return rows


@frappe.whitelist()
def get_course_assessment_progress(course: str, member: str):
	if not can_modify_course(course):
		frappe.throw(
			_("You do not have permission to access this course's assessment data."), frappe.PermissionError
		)

	quizzes = get_course_quiz_progress(course, member)
	assignments = get_course_assignment_progress(course, member)
	programming_exercises = get_course_programming_exercise_progress(course, member)

	return {
		"quizzes": quizzes,
		"assignments": assignments,
		"exercises": programming_exercises,
	}


def get_course_quiz_progress(course: str, member: str):
	quizzes = get_assessment_from_lesson(course, "quiz")
	attempts = []

	for quiz in quizzes:
		submissions = frappe.get_all(
			"LMS Quiz Submission",
			{
				"quiz": quiz,
				"member": member,
			},
			["name", "score", "percentage", "quiz", "quiz_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(submissions):
			attempts.append(submissions[0])
		else:
			attempts.append(
				{
					"quiz": quiz,
					"quiz_title": frappe.db.get_value("LMS Quiz", quiz, "title"),
					"score": 0,
					"percentage": 0,
				}
			)

	return attempts


def get_course_assignment_progress(course: str, member: str):
	assignments = get_assessment_from_lesson(course, "assignment")
	submissions = []

	for assignment in assignments:
		assignment_subs = frappe.get_all(
			"LMS Assignment Submission",
			{
				"assignment": assignment,
				"member": member,
			},
			["name", "status", "assignment", "assignment_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(assignment_subs):
			submissions.append(assignment_subs[0])
		else:
			submissions.append(
				{
					"assignment": assignment,
					"assignment_title": frappe.db.get_value("LMS Assignment", assignment, "title"),
					"status": "Not Submitted",
				}
			)

	return submissions


def get_course_programming_exercise_progress(course: str, member: str):
	exercises = get_assessment_from_lesson(course, "program")
	submissions = []

	for exercise in exercises:
		exercise_subs = frappe.get_all(
			"LMS Programming Exercise Submission",
			{
				"exercise": exercise,
				"member": member,
			},
			["name", "status", "exercise", "exercise_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(exercise_subs):
			submissions.append(exercise_subs[0])
		else:
			submissions.append(
				{
					"exercise": exercise,
					"exercise_title": frappe.db.get_value("LMS Programming Exercise", exercise, "title"),
					"status": "Not Attempted",
				}
			)

	return submissions


def get_assessment_from_lesson(course: str, assessment_type: str):
	assessments = []
	lessons = frappe.get_all("Course Lesson", {"course": course}, ["name", "title", "content"])

	for lesson in lessons:
		if lesson.content:
			content = json.loads(lesson.content)
			for block in content.get("blocks", []):
				if block.get("type") == assessment_type:
					data_field = "exercise" if assessment_type == "program" else assessment_type
					assessment_name = block.get("data", {}).get(data_field)
					assessments.append(assessment_name)

	return assessments


@frappe.whitelist()
def get_badges(member: str):
	if not has_lms_role():
		frappe.throw(_("You do not have permission to access badges."), frappe.PermissionError)

	badges = frappe.get_all(
		"LMS Badge Assignment",
		{"member": member},
		["name", "member", "badge", "badge_image", "badge_description", "issued_on"],
	)

	return badges


@frappe.whitelist()
def clear_demo_data():
	frappe.only_for("Moderator")
	quiz_title = "Do you know Frappe Learning?"
	if frappe.db.exists("LMS Quiz", {"title": quiz_title}):
		frappe.db.delete("LMS Quiz", {"title": quiz_title})

	demo_course = frappe.get_all("LMS Course", {"title": "A guide to Frappe Learning"}, pluck="name")

	if len(demo_course):
		delete_course(demo_course[0])

	users = ["ash@ipp.com", "john.doe@example.com", "jane.smith@example.com", "jannat@example.com"]
	for user in users:
		if frappe.db.exists("User", user):
			frappe.delete_doc("User", user, ignore_permissions=True)

	frappe.db.set_single_value("LMS Settings", "demo_data_present", False)


@frappe.whitelist()
def search_users_by_role(txt: str = "", roles: str | list | None = None, page_length: int = 10):
	"""Returns users with `roles` in search_link format"""
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	if not roles:
		return []

	if isinstance(roles, str):
		roles = json.loads(roles)

	invalid_roles = set(roles) - set(LMS_ROLES)
	if invalid_roles:
		frappe.throw(_("Cannot search for roles: {0}").format(", ".join(invalid_roles)))

	users_with_roles = frappe.get_all(
		"Has Role",
		filters={"role": ["in", roles], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)

	if not users_with_roles:
		return []

	results = frappe.get_all(
		"User",
		filters=[
			["name", "in", users_with_roles],
			["name", "not in", ["Administrator", "Guest"]],
			["enabled", "=", 1],
		],
		or_filters=[
			["full_name", "like", f"%{txt}%"],
			["name", "like", f"%{txt}%"],
		],
		fields=["name", "full_name"],
		limit_page_length=cint(page_length),
		order_by="full_name asc",
	)

	return [
		{"value": r.name, "description": r.full_name or r.name, "label": r.full_name or r.name}
		for r in results
	]


@frappe.whitelist()
def export_course_as_zip(course_name: str):
	if not can_modify_course(course_name):
		frappe.throw(_("You do not have permission to export this course."), frappe.PermissionError)

	export_course_zip(course_name)


@frappe.whitelist()
def import_course_from_zip(zip_file_path: str):
	frappe.only_for(["Moderator", "Course Creator"])
	return import_course_zip(zip_file_path)


@frappe.whitelist()
def import_scorm_course(
	file_name: str,
	course_title: str = None,
	course_name: str = None,
	publish: int = 1,
	scan_package: int = 1,
):
	"""Create a published LMS Course from an uploaded SCORM ZIP File."""
	from lms.lms.scorm_import import import_scorm_course as _import_scorm_course

	return _import_scorm_course(
		file_name=file_name,
		course_title=course_title,
		course_name=course_name,
		publish=publish,
		scan_package=scan_package,
	)


@frappe.whitelist()
def save_lesson_feedback(course: str, chapter: int, lesson: int, reaction: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to submit feedback."))

	if reaction not in ("Yes", "No"):
		frappe.throw(_("Invalid reaction. Must be Yes or No."))

	lesson_name = _resolve_lesson_name(course, int(chapter), int(lesson))
	if not lesson_name:
		frappe.throw(_("Lesson not found."))

	existing = frappe.db.get_value(
		"LMS Lesson Feedback",
		{"lesson": lesson_name, "member": frappe.session.user},
		"name",
	)

	if existing:
		frappe.db.set_value("LMS Lesson Feedback", existing, "reaction", reaction)
		return {"name": existing, "reaction": reaction}
	else:
		doc = frappe.new_doc("LMS Lesson Feedback")
		doc.lesson = lesson_name
		doc.member = frappe.session.user
		doc.reaction = reaction
		doc.insert()
		return {"name": doc.name, "reaction": reaction}


@frappe.whitelist()
def get_lesson_feedback(course: str, chapter: int, lesson: int):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to continue."), frappe.PermissionError)

	lesson_name = _resolve_lesson_name(course, int(chapter), int(lesson))
	if not lesson_name:
		return {"user_reaction": None, "yes_count": 0, "no_count": 0}

	user_reaction = frappe.db.get_value(
		"LMS Lesson Feedback",
		{"lesson": lesson_name, "member": frappe.session.user},
		"reaction",
	)

	yes_count = frappe.db.count(
		"LMS Lesson Feedback", {"lesson": lesson_name, "reaction": "Yes"}
	)
	no_count = frappe.db.count(
		"LMS Lesson Feedback", {"lesson": lesson_name, "reaction": "No"}
	)

	return {
		"user_reaction": user_reaction,
		"yes_count": yes_count,
		"no_count": no_count,
	}


def _resolve_lesson_name(course: str, chapter: int, lesson: int):
	chapter_name = frappe.db.get_value(
		"Chapter Reference", {"parent": course, "idx": chapter}, "chapter"
	)
	if not chapter_name:
		return None
	return frappe.db.get_value(
		"Lesson Reference", {"parent": chapter_name, "idx": lesson}, "lesson"
	)


def _check_lesson_create_permission():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to create lessons."))

	if not frappe.has_permission("Course Lesson", "create"):
		frappe.throw(_("You do not have permission to create lessons."), frappe.PermissionError)


def _validate_lesson_upload_extension(filename: str) -> str:
	extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
	if extension not in ("pdf", "docx"):
		frappe.throw(_("Only PDF and DOCX files are allowed."))
	return extension


def _lesson_content_blocks_from_file(file_url: str, extension: str, file_path: str):
	import json
	import zipfile

	if extension == "docx":
		if zipfile.is_zipfile(file_path):
			content_blocks = _convert_docx_to_blocks(file_path)
		else:
			content_blocks = _convert_text_to_blocks(file_path)
	else:
		content_blocks = [
			{
				"id": frappe.generate_hash(length=10),
				"type": "upload",
				"data": {"file_url": file_url, "file_type": "PDF", "quizzes": []},
			}
		]

	return json.dumps(
		{
			"time": int(frappe.utils.now_datetime().timestamp() * 1000),
			"blocks": content_blocks,
			"version": "2.29.0",
		}
	)


def _create_lesson_from_uploaded_file(course: str, chapter: int, file_url: str, filename: str):
	import os

	_check_lesson_create_permission()
	extension = _validate_lesson_upload_extension(filename)
	lesson_title = filename.rsplit(".", 1)[0] if "." in filename else filename

	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(_("Uploaded file not found. Please upload the file again."))

	file_doc = frappe.get_doc("File", file_name)
	file_path = file_doc.get_full_path()
	if not os.path.exists(file_path):
		frappe.throw(_("Uploaded file not found on disk."))

	if os.path.getsize(file_path) == 0:
		frappe.throw(_("Uploaded file is empty."))

	content_json = _lesson_content_blocks_from_file(file_url, extension, file_path)

	chapter_int = int(chapter)
	chapter_name = frappe.db.get_value(
		"Chapter Reference", {"parent": course, "idx": chapter_int}, "chapter"
	)
	if not chapter_name:
		frappe.throw(_("Chapter not found."))

	existing_lessons = frappe.db.count("Lesson Reference", {"parent": chapter_name})
	new_idx = existing_lessons + 1

	lesson_doc = frappe.get_doc(
		{
			"doctype": "Course Lesson",
			"title": lesson_title,
			"course": course,
			"chapter": chapter_name,
			"content": content_json,
			"include_in_preview": 0,
		}
	)
	lesson_doc.save(ignore_permissions=True)

	chapter_doc = frappe.get_doc("Course Chapter", chapter_name)
	chapter_doc.append("lessons", {"lesson": lesson_doc.name, "idx": new_idx})
	chapter_doc.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"lesson_name": lesson_doc.name,
		"title": lesson_title,
		"chapter_number": chapter_int,
		"lesson_number": new_idx,
	}


@frappe.whitelist()
def create_lesson_from_file(course: str, chapter: int, file_url: str, file_name: str | None = None):
	"""Create a lesson from a file already uploaded via upload_file."""
	filename = file_name or frappe.db.get_value("File", {"file_url": file_url}, "file_name")
	if not filename:
		frappe.throw(_("File name is required."))
	return _create_lesson_from_uploaded_file(course, chapter, file_url, filename)


@frappe.whitelist()
def upload_and_create_lesson(course: str, chapter: int):
	"""Upload a PDF/DOCX file and auto-create a lesson with it as content."""
	import os
	import shutil
	import tempfile

	_check_lesson_create_permission()

	files = frappe.request.files
	if not files or "file" not in files:
		frappe.throw(_("No file uploaded."))

	uploaded_file = files["file"]
	filename = uploaded_file.filename
	extension = _validate_lesson_upload_extension(filename)
	lesson_title = filename.rsplit(".", 1)[0] if "." in filename else filename

	tmp = tempfile.NamedTemporaryFile(delete=False, suffix="." + extension)
	uploaded_file.save(tmp)
	tmp.close()
	tmp_path = tmp.name

	file_size = os.path.getsize(tmp_path)
	if file_size == 0:
		os.unlink(tmp_path)
		frappe.throw(_("Uploaded file is empty."))

	public_files_dir = os.path.join(frappe.get_site_path(), "public", "files")
	os.makedirs(public_files_dir, exist_ok=True)
	safe_filename = frappe.scrub(lesson_title) + "." + extension
	dest_path = os.path.join(public_files_dir, safe_filename)
	counter = 1
	while os.path.exists(dest_path):
		safe_filename = frappe.scrub(lesson_title) + f"_{counter}." + extension
		dest_path = os.path.join(public_files_dir, safe_filename)
		counter += 1

	shutil.move(tmp_path, dest_path)

	file_url = "/files/" + safe_filename
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"file_url": file_url,
		"is_private": 0,
		"file_size": file_size,
	})
	file_doc.insert(ignore_permissions=True)

	return _create_lesson_from_uploaded_file(course, chapter, file_url, filename)


@frappe.whitelist()
def create_lesson_from_file(course: str, chapter: int, file_url: str, file_name: str | None = None):
	"""Create a lesson from a file already uploaded via upload_file."""
	filename = file_name or frappe.db.get_value("File", {"file_url": file_url}, "file_name")
	if not filename:
		frappe.throw(_("File name is required."))
	return _create_lesson_from_uploaded_file(course, chapter, file_url, filename)


@frappe.whitelist()
def upload_and_create_lesson(course: str, chapter: int):
	"""Upload a PDF/DOCX file and auto-create a lesson with it as content."""
	import os
	import shutil
	import tempfile

	_check_lesson_create_permission()

	files = frappe.request.files
	if not files or "file" not in files:
		frappe.throw(_("No file uploaded."))

	uploaded_file = files["file"]
	filename = uploaded_file.filename
	extension = _validate_lesson_upload_extension(filename)
	lesson_title = filename.rsplit(".", 1)[0] if "." in filename else filename

	tmp = tempfile.NamedTemporaryFile(delete=False, suffix="." + extension)
	uploaded_file.save(tmp)
	tmp.close()
	tmp_path = tmp.name

	file_size = os.path.getsize(tmp_path)
	if file_size == 0:
		os.unlink(tmp_path)
		frappe.throw(_("Uploaded file is empty."))

	public_files_dir = os.path.join(frappe.get_site_path(), "public", "files")
	os.makedirs(public_files_dir, exist_ok=True)
	safe_filename = frappe.scrub(lesson_title) + "." + extension
	dest_path = os.path.join(public_files_dir, safe_filename)
	counter = 1
	while os.path.exists(dest_path):
		safe_filename = frappe.scrub(lesson_title) + f"_{counter}." + extension
		dest_path = os.path.join(public_files_dir, safe_filename)
		counter += 1

	shutil.move(tmp_path, dest_path)

	file_url = "/files/" + safe_filename
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"file_url": file_url,
		"is_private": 0,
		"file_size": file_size,
	})
	file_doc.insert(ignore_permissions=True)

	return _create_lesson_from_uploaded_file(course, chapter, file_url, filename)


def _convert_docx_to_blocks(file_path: str):
	"""Convert a DOCX file to EditorJS blocks using mammoth."""
	try:
		import mammoth
	except ImportError:
		frappe.throw(_("mammoth library is required for DOCX conversion. Please install it."))

	with open(file_path, "rb") as f:
		result = mammoth.convert_to_html(f)

	html = result.value
	if not html.strip():
		return [
			{
				"id": frappe.generate_hash(length=10),
				"type": "paragraph",
				"data": {"text": "Empty document"},
			}
		]

	blocks = []
	from html.parser import HTMLParser

	class DocxBlockParser(HTMLParser):
		def __init__(self):
			super().__init__()
			self.current_text = ""
			self.current_tag = None
			self.in_list = False
			self.list_items = []
			self.list_style = "unordered"

		def handle_starttag(self, tag, attrs):
			if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
				self.flush_text()
				self.current_tag = tag
			elif tag == "p":
				self.flush_text()
				self.current_tag = "p"
			elif tag == "ol":
				self.flush_text()
				self.in_list = True
				self.list_style = "ordered"
				self.list_items = []
			elif tag == "ul":
				self.flush_text()
				self.in_list = True
				self.list_style = "unordered"
				self.list_items = []
			elif tag == "li":
				self.current_text = ""
			elif tag in ("strong", "b"):
				self.current_text += "<b>"
			elif tag in ("em", "i"):
				self.current_text += "<i>"
			elif tag == "a":
				href = dict(attrs).get("href", "")
				self.current_text += f'<a href="{href}">'
			elif tag == "br":
				self.current_text += "<br>"
			elif tag == "img":
				self.flush_text()
				src = dict(attrs).get("src", "")
				if src:
					blocks.append({
						"id": frappe.generate_hash(length=10),
						"type": "image",
						"data": {"url": src, "caption": "", "withBorder": False, "stretched": False, "withBackground": False},
					})

		def handle_endtag(self, tag):
			if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
				level = int(tag[1])
				text = self.current_text.strip()
				if text:
					blocks.append({
						"id": frappe.generate_hash(length=10),
						"type": "header",
						"data": {"text": text, "level": level},
					})
				self.current_text = ""
				self.current_tag = None
			elif tag == "p":
				text = self.current_text.strip()
				if text:
					blocks.append({
						"id": frappe.generate_hash(length=10),
						"type": "paragraph",
						"data": {"text": text},
					})
				self.current_text = ""
				self.current_tag = None
			elif tag in ("ol", "ul"):
				if self.list_items:
					blocks.append({
						"id": frappe.generate_hash(length=10),
						"type": "list",
						"data": {"style": self.list_style, "items": self.list_items},
					})
				self.in_list = False
				self.list_items = []
			elif tag == "li":
				text = self.current_text.strip()
				if text:
					self.list_items.append(text)
				self.current_text = ""
			elif tag in ("strong", "b"):
				self.current_text += "</b>"
			elif tag in ("em", "i"):
				self.current_text += "</i>"
			elif tag == "a":
				self.current_text += "</a>"

		def handle_data(self, data):
			self.current_text += data

		def flush_text(self):
			if self.current_text.strip() and not self.in_list and self.current_tag is None:
				blocks.append({
					"id": frappe.generate_hash(length=10),
					"type": "paragraph",
					"data": {"text": self.current_text.strip()},
				})
				self.current_text = ""

	parser = DocxBlockParser()
	parser.feed(html)
	parser.flush_text()

	if not blocks:
		blocks.append({
			"id": frappe.generate_hash(length=10),
			"type": "paragraph",
			"data": {"text": html},
		})

	return blocks


def _convert_text_to_blocks(file_path: str):
	"""Convert a plain text or Markdown file to EditorJS blocks."""
	with open(file_path, "r", encoding="utf-8", errors="replace") as f:
		text = f.read()

	blocks = []
	for line in text.split("\n"):
		stripped = line.strip()
		if not stripped:
			continue

		if stripped.startswith("######"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 6}})
		elif stripped.startswith("#####"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 5}})
		elif stripped.startswith("####"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 4}})
		elif stripped.startswith("###"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 3}})
		elif stripped.startswith("##"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 2}})
		elif stripped.startswith("#"):
			blocks.append({"id": frappe.generate_hash(length=10), "type": "header", "data": {"text": stripped.lstrip("#").strip(), "level": 1}})
		elif stripped.startswith("- ") or stripped.startswith("* "):
			if blocks and blocks[-1]["type"] == "list" and blocks[-1]["data"]["style"] == "unordered":
				blocks[-1]["data"]["items"].append(stripped[2:].strip())
			else:
				blocks.append({"id": frappe.generate_hash(length=10), "type": "list", "data": {"style": "unordered", "items": [stripped[2:].strip()]}})
		elif len(stripped) > 1 and stripped[0].isdigit() and (stripped[1] == "." or (stripped[1].isdigit() and stripped[2] == ".")):
			item_text = stripped.split(".", 1)[1].strip() if "." in stripped else stripped
			if blocks and blocks[-1]["type"] == "list" and blocks[-1]["data"]["style"] == "ordered":
				blocks[-1]["data"]["items"].append(item_text)
			else:
				blocks.append({"id": frappe.generate_hash(length=10), "type": "list", "data": {"style": "ordered", "items": [item_text]}})
		else:
			md_line = stripped.replace("**", "<b>").replace("__", "<b>").replace("*", "<i>").replace("_", "<i>")
			blocks.append({"id": frappe.generate_hash(length=10), "type": "paragraph", "data": {"text": md_line}})

	if not blocks:
		blocks.append({"id": frappe.generate_hash(length=10), "type": "paragraph", "data": {"text": text[:500]}})

	return blocks


@frappe.whitelist()
def get_folder_tree():
	folders = frappe.get_all(
		"LMS Quiz Folder",
		fields=["name", "title", "parent_quiz_folder"],
		order_by="title asc",
	)

	# Frappe disallows raw SQL in get_all fields (e.g. count(name)); use SQL or aggregate in Python.
	quiz_counts = {}
	for row in frappe.db.sql(
		"""
		SELECT quiz_folder, COUNT(*) as cnt
		FROM `tabLMS Quiz`
		GROUP BY `quiz_folder`
		""",
		as_dict=True,
	):
		key = row.quiz_folder or "__unfiled__"
		quiz_counts[key] = cint(row.cnt)

	folder_map = {}
	for f in folders:
		folder_map[f.name] = {
			"name": f.name,
			"title": f.title,
			"parent_quiz_folder": f.parent_quiz_folder,
			"quiz_count": quiz_counts.get(f.name, 0),
			"children": [],
		}

	roots = []
	for f in folders:
		node = folder_map[f.name]
		parent = f.parent_quiz_folder
		if parent and parent in folder_map:
			folder_map[parent]["children"].append(node)
		else:
			roots.append(node)

	return {
		"folders": roots,
		"unfiled_count": quiz_counts.get("__unfiled__", 0),
		"total_count": sum(quiz_counts.values()),
	}


@frappe.whitelist()
def move_quiz_to_folder(quiz: str, folder: str | None = None):
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	quiz_doc.quiz_folder = folder or None
	quiz_doc.save(ignore_permissions=False)
	return {"success": True}


@frappe.whitelist()
def rename_quiz_folder(folder: str, new_title: str):
	folder_doc = frappe.get_doc("LMS Quiz Folder", folder)
	folder_doc.title = new_title
	folder_doc.save(ignore_permissions=False)
	return {"success": True, "name": folder_doc.name, "title": folder_doc.title}
