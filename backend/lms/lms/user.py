import re

import frappe
from frappe import _
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, escape_html, random_string, validate_email_address
from frappe.website.utils import cleanup_page_name, is_signup_disabled

from lms.lms.utils import get_country_code, get_lms_route

PHONE_DIGITS_RE = re.compile(r"^\d{8,15}$")


def validate_username_duplicates(doc, method):
	while not doc.username or doc.username_exists():
		doc.username = append_number_if_name_exists(
			doc.doctype, cleanup_page_name(doc.full_name), fieldname="username"
		)
	if " " in doc.username:
		doc.username = doc.username.replace(" ", "")

	if len(doc.username) < 4:
		doc.username = doc.email.replace("@", "").replace(".", "")


def add_lms_student_role(doc, method):
	doc.append_roles("LMS Student")


def _normalize_phone(phone: str) -> str:
	return re.sub(r"\D", "", str(phone or "").strip())


def _validate_signup_payload(
	email: str,
	first_name: str,
	last_name: str,
	phone: str = None,
	school_name: str = None,
	verify_terms=None,
):
	missing = []
	if not first_name:
		missing.append(_("Full Name"))
	if not email:
		missing.append(_("Email"))

	if missing:
		frappe.throw(
			_("Please complete all required fields: {0}").format(", ".join(missing)),
			frappe.ValidationError,
		)

	if not validate_email_address(email):
		frappe.throw(_("Please enter a valid email address"), frappe.ValidationError)

	phone_digits = _normalize_phone(phone)
	if phone and not PHONE_DIGITS_RE.match(phone_digits):
		frappe.throw(_("Phone Number must contain 8–15 digits only"), frappe.ValidationError)

	return phone_digits or ""


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def sign_up(
	email: str = None,
	first_name: str = None,
	last_name: str = None,
	phone: str = None,
	school_name: str = None,
	verify_terms: bool = False,
	user_category: str = None,
	full_name: str = None,
):
	"""Create a website user after validating enrollment signup fields.

	Enrollment / learning access happens after login. This method gates User
	creation (and the subsequent welcome / onboarding email) on required
	profile fields and Terms & Conditions acceptance.
	"""
	if is_signup_disabled():
		frappe.throw(_("Sign Up is disabled"), _("Not Allowed"))

	email = (email or "").strip()
	first_name = escape_html((first_name or "").strip())
	last_name = escape_html((last_name or "").strip())
	school_name = escape_html((school_name or "").strip())
	user_category = (user_category or "").strip()

	# Backward compatibility: older clients sent a single full_name
	if (not first_name or not last_name) and full_name:
		parts = escape_html((full_name or "").strip()).split(None, 1)
		if not first_name and parts:
			first_name = parts[0]
		if not last_name and len(parts) > 1:
			last_name = parts[1]
		elif not last_name:
			last_name = "-"

	phone_digits = _validate_signup_payload(
		email=email,
		first_name=first_name,
		last_name=last_name,
		phone=phone,
		school_name=school_name,
		verify_terms=verify_terms,
	)

	user = frappe.db.get("User", {"email": email})
	if user:
		if user.enabled:
			return 0, _("Already Registered")
		else:
			return 0, _("Registered but disabled")
	else:
		max_signups_allowed_per_hour = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
		users_created_past_hour = frappe.db.get_creation_count("User", 60)
		if users_created_past_hour >= max_signups_allowed_per_hour:
			frappe.respond_as_web_page(
				_("Temporarily Disabled"),
				_(
					"Too many users signed up recently, so the registration is disabled. Please try back in an hour"
				),
				http_status_code=429,
			)

	user_doc = {
		"doctype": "User",
		"email": email,
		"first_name": first_name,
		"last_name": last_name,
		"mobile_no": phone_digits,
		"verify_terms": 1 if cint(verify_terms) else 0,
		"user_category": user_category,
		"country": "",
		"enabled": 1,
		"new_password": random_string(10),
		"user_type": "Website User",
	}

	# Prefer dedicated school_name custom field when present; also keep college in sync
	meta = frappe.get_meta("User")
	if meta.has_field("school_name"):
		user_doc["school_name"] = school_name
	if meta.has_field("college"):
		user_doc["college"] = school_name

	user = frappe.get_doc(user_doc)
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True
	user.insert()

	# set default signup role as per Portal Settings
	default_role = frappe.db.get_single_value("Portal Settings", "default_role")
	if default_role:
		user.add_roles(default_role)

	user.add_roles("LMS Student")
	set_country_from_ip(None, user.name)

	if user.flags.email_sent:
		return 1, _("Please check your email for verification")
	else:
		return 2, _("Please ask your administrator to verify your sign-up")


def set_country_from_ip(login_manager: object = None, user: str = None):
	if not user and login_manager:
		user = login_manager.user
	user_country = frappe.db.get_value("User", user, "country")
	if user_country:
		return
	frappe.db.set_value("User", user, "country", get_country_code())
	return


def on_login(login_manager):
	frappe.local.response["home_page"] = "/dashboard"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def login_via_key(key: str):
	"""Frappe's one-time email login, but always landing on the LMS portal.

	Same key handling as frappe.www.login.login_via_key; only the destination differs.
	"""
	from frappe import _

	cache_key = f"one_time_login_key:{key}"
	email = frappe.cache.get_value(cache_key)
	if not email:
		frappe.respond_as_web_page(
			_("Link expired"),
			_("This sign-in link is invalid or has expired. Please request a new one from the login page."),
			http_status_code=403,
			indicator_color="red",
		)
		return

	frappe.cache.delete_value(cache_key)
	frappe.local.login_manager.login_as(email)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/dashboard"


@frappe.whitelist()
def logout():
	"""Force portal logout to /login — never Frappe Desk."""
	frappe.local.login_manager.logout()
	frappe.local.response["message"] = "Logged out"
	frappe.local.response["home_page"] = "/login"
