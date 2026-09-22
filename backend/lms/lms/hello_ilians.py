# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""'Hello ILians': the joining form a new Sales joiner fills once, before CRT 1 opens."""

import frappe
from frappe import _
from frappe.utils import now_datetime

DOCTYPE = "LMS Onboarding Form"

TEAM_LEADS = [
	"anteryami.panda@infinitylearn.com",
	"umang.kumar@infinitylearn.com",
	"shashi.suman@infinitylearn.com",
	"ritik.anand@infinitylearn.com",
	"ratnesh.mishra@infinitylearn.com",
	"yakub.pasha@infinitylearn.com",
	"soheb.murshed@infinitylearn.com",
	"prem.gupta@infinitylearn.com",
]
EXPERIENCE = ["Fresher", "<6", "6-12", "12-24", "24-36", "36+"]
DISTANCE = ["<5km", "5-10km", "10-15km", "15-20km", ">20km"]
LANGUAGES = [
	"Hindi", "English", "Bengali", "Telugu", "Marathi", "Tamil", "Urdu", "Gujarati",
	"Kannada", "Odia", "Malayalam", "Punjabi", "Assamese", "Bhojpuri", "Maithili",
]
STATES = [
	"Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
	"Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
	"Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
	"Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
	"Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
	"Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]
FIELDS = [
	"first_name", "last_name", "employee_code", "joining_date", "ac_name", "ac_email", "team_lead",
	"phone", "alternate_phone", "distance_from_office", "home_state", "city", "primary_language",
	"other_languages", "experience", "previous_company", "edtech_experience", "last_edtech_company",
]
REQUIRED = [
	"first_name", "joining_date", "ac_name", "ac_email", "team_lead", "phone", "alternate_phone",
	"distance_from_office", "home_state", "primary_language", "other_languages", "experience",
	"previous_company", "edtech_experience",
]


def _ready():
	return frappe.db.exists("DocType", DOCTYPE)


def is_submitted(user=None):
	user = user or frappe.session.user
	return bool(_ready() and frappe.db.get_value(DOCTYPE, user, "submitted_on"))


def is_required(user=None):
	"""Learners must fill it before CRT 1. Staff (trainers, admins) skip it."""
	from lms.lms.sales_journey import _is_staff

	user = user or frappe.session.user
	return bool(_ready() and user != "Guest" and not _is_staff(user) and not is_submitted(user))


@frappe.whitelist()
def get_form():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	user = frappe.session.user
	values = {}
	if _ready() and frappe.db.exists(DOCTYPE, user):
		values = frappe.db.get_value(DOCTYPE, user, FIELDS + ["submitted_on"], as_dict=True)
	else:
		profile = frappe.db.get_value("User", user, ["first_name", "last_name", "mobile_no"], as_dict=True) or {}
		values = {"first_name": profile.get("first_name"), "last_name": profile.get("last_name"), "phone": profile.get("mobile_no")}
	return {
		"email": user,
		"values": values,
		"submitted": bool(values.get("submitted_on")),
		"options": {
			"team_leads": [{"value": e, "label": frappe.db.get_value("User", e, "full_name") or _name_from_email(e)} for e in TEAM_LEADS],
			"experience": EXPERIENCE,
			"distance": DISTANCE,
			"languages": LANGUAGES,
			"states": STATES,
		},
	}


def _name_from_email(email):
	return " ".join(p.capitalize() for p in email.split("@")[0].replace("_", ".").split("."))


@frappe.whitelist()
def submit_form(values: dict | str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if isinstance(values, str):
		values = frappe.parse_json(values)
	user = frappe.session.user
	data = {k: (values.get(k) or "").strip() if isinstance(values.get(k), str) else values.get(k) for k in FIELDS}

	missing = [k for k in REQUIRED if not data.get(k)]
	if missing:
		frappe.throw(_("Please fill: {0}").format(", ".join(k.replace("_", " ") for k in missing)))
	if data["edtech_experience"] == "Yes" and not data.get("last_edtech_company"):
		frappe.throw(_("Please enter your last EdTech company."))
	if data["team_lead"] not in TEAM_LEADS:
		frappe.throw(_("Pick your Training Manager from the list."))
	if not frappe.utils.validate_email_address(data["ac_email"]):
		frappe.throw(_("Enter a valid AC email."))

	doc = frappe.get_doc(DOCTYPE, user) if frappe.db.exists(DOCTYPE, user) else frappe.new_doc(DOCTYPE)
	doc.member = user
	# The employee code belongs to the admin who assigns it (and is logged when it changes), so the
	# joining form shows it but can never set it.
	data["employee_code"] = frappe.db.get_value("User", user, "employee_code") or doc.get("employee_code") or ""
	doc.update(data)
	doc.submitted_on = doc.submitted_on or now_datetime()
	doc.save(ignore_permissions=True)

	# Keep the account profile in step with what they told us.
	frappe.db.set_value(
		"User",
		user,
		{"first_name": data["first_name"], "last_name": data.get("last_name") or "", "mobile_no": data["phone"]},
	)
	return {"submitted": True}


@frappe.whitelist()
def get_responses():
	"""All answers, for admins (scoped to people they can see)."""
	from lms.lms import access

	if not access.is_admin():
		frappe.throw(_("Only admins can see onboarding responses."), frappe.PermissionError)
	rows = frappe.get_all(DOCTYPE, fields=["member", "employee_name"] + FIELDS[2:] + ["submitted_on"], order_by="submitted_on desc")
	return access.filter_rows_by_email(rows, field="member")
