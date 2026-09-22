import frappe

from . import __version__ as app_version

app_name = "frappe_lms"
app_title = "LMS"
app_publisher = "Varsity Education"
app_description = "Sales onboarding and classroom readiness training platform"
app_icon_url = "/assets/lms/images/il-favicon.png"
app_icon_title = "LMS"
app_icon_route = "/dashboard"
# Desk navbar logo, splash screen and favicon — Infinity Learn instead of Frappe.
app_logo_url = "/assets/lms/images/il-favicon.png"
website_context = {
	"favicon": "/assets/lms/images/il-favicon.png",
	"splash_image": "/assets/lms/images/il-favicon.png",
}
app_color = "grey"
app_email = "jannat@frappe.io"
app_license = "AGPL"
required_apps = ["frappe/payments"]


def get_lms_path():
	configured = None
	if frappe.conf:
		configured = frappe.conf.get("lms_path")
	if configured in (None, False, ""):
		return ""
	return str(configured).strip("/")


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lms/css/lms.css"
# app_include_js = "/assets/lms/js/lms.js"

def _versioned_asset(path):
	"""Append a content hash so browsers pick up a fresh copy after each deploy.

	nginx serves /assets with a long max-age and these URLs carry no build hash.
	"""
	import hashlib
	import os

	file_path = os.path.join(os.path.dirname(__file__), "public", path.removeprefix("/assets/lms/"))
	try:
		with open(file_path, "rb") as f:
			return f"{path}?v={hashlib.md5(f.read(), usedforsecurity=False).hexdigest()[:10]}"
	except OSError:
		return path


# include js, css files in header of web template
# Auth CSS/JS are scoped to /login and /update-password (see il-auth.js).
web_include_css = [_versioned_asset("/assets/lms/css/il-auth.css")]
web_include_js = [_versioned_asset("/assets/lms/js/il-auth.js")]

# Infinity Learn styles inlined into outgoing emails
email_css = ["/assets/lms/css/il-email.css"]

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "lms.install.before_install"
after_install = "lms.install.after_install"
before_uninstall = "lms.install.before_uninstall"
# after_sync is not a Frappe hook, so these never ran; after_migrate runs on every deploy.
after_migrate = [
	"lms.install.after_sync",
	"lms.lms.org.seed_departments",
	"lms.lms.content_scope.tag_existing_content",
	"lms.lms.day_journey.setup_crt_journey",
	"lms.sqlite.build_index_in_background",
]

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"LMS Course": "lms.lms.content_scope.course_query_conditions",
	"LMS Batch": "lms.lms.content_scope.batch_query_conditions",
	"LMS Program": "lms.lms.content_scope.program_query_conditions",
	"LMS Certificate": "lms.lms.doctype.lms_certificate.lms_certificate.get_permission_query_conditions",
	"Sales Training Evaluation": "lms.lms.sales_journey.get_permission_query_conditions",
	"Sales OJT Attempt": "lms.lms.sales_journey.get_ojt_permission_query_conditions",
}

has_permission = {
	"LMS Course": "lms.lms.content_scope.has_course_permission",
	"LMS Live Class": "lms.lms.doctype.lms_live_class.lms_live_class.has_permission",
	"LMS Batch": "lms.lms.doctype.lms_batch.lms_batch.has_permission",
	"LMS Program": "lms.lms.doctype.lms_program.lms_program.has_permission",
	"LMS Certificate": "lms.lms.doctype.lms_certificate.lms_certificate.has_permission",
	"Sales Training Evaluation": "lms.lms.sales_journey.has_permission",
	"Sales OJT Attempt": "lms.lms.sales_journey.has_ojt_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Web Template": "lms.overrides.web_template.CustomWebTemplate",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"*": {
		"on_change": [
			"lms.lms.doctype.lms_badge.lms_badge.process_badges",
		]
	},
	"Discussion Reply": {
		"after_insert": "lms.lms.utils.handle_notifications",
		"validate": "lms.lms.utils.validate_discussion_reply",
	},
	"Notification Log": {"on_change": "lms.lms.utils.publish_notifications"},
	"User": {
		"validate": "lms.lms.user.validate_username_duplicates",
		"before_insert": "lms.lms.user.add_lms_student_role",
		"on_update": "lms.lms.org.on_user_update",
	},
	"Google Calendar": {
		"on_update": "lms.lms.library.handle_google_account_change_hook",
	},
	"LMS Course": {"validate": "lms.lms.content_scope.set_team"},
	"LMS Batch": {"validate": "lms.lms.content_scope.set_team"},
	"LMS Program": {"validate": "lms.lms.content_scope.set_team"},
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"all": [
		"lms.sqlite.build_index_in_background",
	],
	"hourly": [
		"lms.lms.doctype.lms_certificate_request.lms_certificate_request.schedule_evals",
		"lms.lms.doctype.lms_course.lms_course.update_course_statistics",
		"lms.lms.doctype.lms_certificate_request.lms_certificate_request.mark_eval_as_completed",
		"lms.lms.doctype.lms_live_class.lms_live_class.update_attendance",
		"lms.lms.library.scheduled_sync_all_recordings",
		"lms.lms.library.sync_after_recent_classes",
	],
	"daily": [
		"lms.job.doctype.job_opportunity.job_opportunity.update_job_openings",
		"lms.lms.doctype.lms_payment.lms_payment.send_payment_reminder",
		"lms.lms.doctype.lms_batch.lms_batch.send_batch_start_reminder",
		"lms.lms.doctype.lms_live_class.lms_live_class.send_live_class_reminder",
		"lms.lms.doctype.lms_course.lms_course.send_notification_for_published_courses",
		"lms.tracking.aggregate_daily_activity",
	],
	"weekly": [
		"lms.tracking.purge_old_heartbeats",
	],
}

fixtures = ["Custom Field", "Function", "Industry", "LMS Category"]

# Testing
# -------

# before_tests = "lms.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	# "frappe.desk.search.get_names_for_mentions": "lms.lms.utils.get_names_for_mentions",
	"frappe.utils.print_format.download_pdf": "lms.lms.doctype.lms_certificate.lms_certificate.download_pdf",
	"logout": "lms.lms.user.logout",
	# Email login links land on the LMS dashboard, not Desk (Frappe sends System Users to /app).
	"frappe.www.login.login_via_key": "lms.lms.user.login_via_key",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# SPA is served by SalesLmsSpaRenderer for allowlisted paths.
# Do NOT use /<path:app_path> → _lms; that steals /login and /app.
# /lms/* redirects are handled in lms.lms.routing.resolve_sales_lms_path (website_path_resolver).
website_route_rules = [
	{
		"from_route": "/courses/<course_name>/<certificate_id>",
		"to_route": "certificate",
	},
]

website_redirects = [
	{"source": "/update-profile", "target": "/edit-profile", "redirect_http_status": 302},
	{"source": "/statistics", "target": "/analytics-dashboard", "redirect_http_status": 302},
]

get_website_user_home_page = "lms.lms.routing.get_website_user_home_page"
website_path_resolver = ["lms.lms.routing.resolve_sales_lms_path"]

update_website_context = [
	"lms.widgets.update_website_context",
]

jinja = {
	"methods": [
		"lms.lms.utils.get_lesson_count",
		"lms.lms.utils.get_instructors",
		"lms.lms.utils.get_lesson_index",
		"lms.lms.utils.get_lesson_url",
		"lms.lms.utils.get_lms_route",
		"lms.lms.utils.is_instructor",
		"lms.lms.utils.get_palette",
		"lms.lms.doctype.lms_certificate.lms_certificate.get_genius_certificate_bg_uri",
	],
	"filters": [],
}

extend_bootinfo = [
	"lms.lms.utils.extend_bootinfo",
]
## Specify the additional tabs to be included in the user profile page.
## Each entry must be a subclass of lms.lms.plugins.ProfileTab
# profile_tabs = []

## Specify the extension to be used to control what scripts and stylesheets
## to be included in lesson pages. The specified value must be be a
## subclass of lms.plugins.PageExtension
# lms_lesson_page_extension = None

# lms_lesson_page_extensions = [
# 	"lms.plugins.LiveCodeExtension"
# ]

has_website_permission = {
	"LMS Certificate Evaluation": "lms.lms.doctype.lms_certificate_evaluation.lms_certificate_evaluation.has_website_permission",
	"LMS Certificate": "lms.lms.doctype.lms_certificate.lms_certificate.has_website_permission",
}

## Markdown Macros for Lessons
lms_markdown_macro_renderers = {
	"Exercise": "lms.plugins.exercise_renderer",
	"Quiz": "lms.plugins.quiz_renderer",
	"YouTubeVideo": "lms.plugins.youtube_video_renderer",
	"Video": "lms.plugins.video_renderer",
	"Assignment": "lms.plugins.assignment_renderer",
	"Embed": "lms.plugins.embed_renderer",
	"Audio": "lms.plugins.audio_renderer",
	"PDF": "lms.plugins.pdf_renderer",
}

page_renderer = [
	"lms.page_renderers.SCORMRenderer",
	"lms.page_renderers.SalesLmsSpaRenderer",
]

# set this to "/" to have profiles on the top-level
profile_url_prefix = "/users/"

signup_form_template = "lms.plugins.show_custom_signup"

on_login = "lms.lms.user.on_login"

get_site_info = "lms.activation.get_site_info"

add_to_apps_screen = [
	{
		"name": "lms",
		"logo": "/assets/lms/images/il-favicon.png",
		"title": "Learning",
		"route": "/dashboard",
		"has_permission": "lms.lms.api.check_app_permission",
	}
]

sqlite_search = ["lms.sqlite.LearningSearch"]
auth_hooks = ["lms.auth.authenticate"]
require_type_annotated_api_methods = True

before_request = [
	"lms.lms.routing.block_desk_portal_routes",
	"lms.lms.google_oauth.patch_google_calendar_scopes",
	"lms.lms.request_hooks.extend_lesson_upload_limit",
	"lms.lms.request_hooks.rewrite_progress_like_filters",
]
