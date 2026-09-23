# Copyright (c) 2026, Infinity Learn and contributors
# For license information, please see license.txt

"""A learner's identity: login email and employee code, and the audit trail of changes to them.

People are sometimes created with a personal email and moved to their work email later, and
employee codes are often not known on day one (a TEMP-#### placeholder is given). Changing either
must never lose progress: the email is the account's ID, so it is changed with Frappe's rename,
which moves every enrollment, lesson progress, quiz, viva and reporting line to the new ID.
Every change is written to LMS Identity Change; learners see their own history, admins and
managers see it for the people they manage.
"""

from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.utils import now_datetime

from lms.lms import access

LOG = "LMS Identity Change"
TEMP_PREFIX = "TEMP-"


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


# Fields the HR roster fills in: the code identifies the person, the rest is who they are at work.
ROSTER_FIELDS = (
	{
		"fieldname": "employee_code",
		"label": "Employee code",
		"insert_after": "last_name",
		"search_index": 1,
		"in_standard_filter": 1,
		"description": "TEMP-#### until the real code is known. Changes are logged.",
	},
	{
		"fieldname": "designation",
		"label": "Designation",
		"insert_after": "employee_code",
		"description": "Job title from the HR roster, e.g. Senior Manager.",
	},
	{
		"fieldname": "grade",
		"label": "Grade",
		"insert_after": "designation",
		"in_standard_filter": 1,
		"description": "Band from the HR roster, e.g. L2.",
	},
)


def setup():
	"""after_migrate: the roster fields on User, and a placeholder code for everyone without one."""
	added = False
	for field in ROSTER_FIELDS:
		if frappe.db.exists("Custom Field", {"dt": "User", "fieldname": field["fieldname"]}):
			continue
		frappe.get_doc({"doctype": "Custom Field", "dt": "User", "fieldtype": "Data", **field}).insert(
			ignore_permissions=True
		)
		added = True
	if added:
		frappe.clear_cache(doctype="User")
	if not frappe.db.has_column("User", "employee_code"):
		return
	for user in frappe.get_all(
		"User",
		{"name": ["not in", ["Administrator", "Guest"]], "employee_code": ["in", ["", None]]},
		pluck="name",
	):
		frappe.db.set_value("User", user, "employee_code", next_temp_code(), update_modified=False)


def next_temp_code() -> str:
	# Two accounts created at once would otherwise both read the same highest code.
	frappe.db.sql("select name from `tabUser` where employee_code like %s order by employee_code desc limit 1 for update", f"{TEMP_PREFIX}%")
	codes = frappe.get_all("User", {"employee_code": ["like", f"{TEMP_PREFIX}%"]}, pluck="employee_code")
	highest = max((int(c[len(TEMP_PREFIX):]) for c in codes if c[len(TEMP_PREFIX):].isdigit()), default=0)
	return f"{TEMP_PREFIX}{highest + 1:04d}"


def assign_code(doc, method=None):
	"""User before_insert: every new account starts with a placeholder employee code."""
	if doc.meta.has_field("employee_code") and not doc.get("employee_code") and doc.name not in ("Administrator", "Guest"):
		doc.employee_code = next_temp_code()


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def _can_view(user: str, viewer: str) -> bool:
	return viewer == user or access.is_super_admin(viewer) or access.can_view_member(user, viewer)


def _can_edit(user: str, editor: str) -> bool:
	"""Super Admins anywhere; team admins only for learners placed in one of their teams.

	Changing someone's login email hands their account to whoever controls the new address, so a
	team admin may never touch staff accounts or people not (yet) in their own teams.
	"""
	if editor == user or not access.is_admin(editor):
		return False
	if access.is_super_admin(editor):
		return True
	if access.get_tier(user) >= access.ADMIN or set(frappe.get_roles(user)) & {"System Manager", "Moderator"}:
		return False
	from lms.lms.team_access import _my_teams

	teams = _my_teams()
	if teams is None:
		return False  # an admin not placed in any team can't be scoped: only Super Admins act
	current = set(
		frappe.get_all("LMS Member Department", {"parenttype": "LMS Member", "parent": user}, pluck="department")
	)
	return bool(current & teams)


def _log(user, field, old, new, reason):
	frappe.get_doc(
		{
			"doctype": LOG,
			"member": user,
			"member_name": frappe.db.get_value("User", user, "full_name"),
			"field": field,
			"old_value": old or "",
			"new_value": new or "",
			"changed_by": frappe.session.user,
			"changed_on": now_datetime(),
			"reason": (reason or "")[:500],
		}
	).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_identity(user: str | None = None):
	viewer = frappe.session.user
	user = user or viewer
	if viewer == "Guest" or not _can_view(user, viewer):
		frappe.throw(_("You can't see this person's account history."), frappe.PermissionError)
	info = frappe.db.get_value(
		"User", user, ["name", "email", "full_name", "employee_code", "designation", "grade"], as_dict=True
	)
	if not info:
		frappe.throw(_("User not found."))
	history = frappe.get_all(
		LOG,
		{"member": user},
		["field", "old_value", "new_value", "changed_by", "changed_on", "reason"],
		order_by="changed_on desc",
	)
	names = {h.changed_by for h in history}
	full = {u.name: u.full_name for u in frappe.get_all("User", {"name": ["in", list(names) or [""]]}, ["name", "full_name"])}
	for h in history:
		h.changed_by_name = full.get(h.changed_by) or h.changed_by
	return {
		"user": info.name,
		"email": info.email or info.name,
		"full_name": info.full_name,
		"employee_code": info.get("employee_code"),
		"designation": info.get("designation"),
		"grade": info.get("grade"),
		"is_temp_code": (info.get("employee_code") or "").startswith(TEMP_PREFIX),
		"can_edit": _can_edit(user, viewer),
		"history": history,
	}


@frappe.whitelist(methods=["POST"])
def set_employee_code(user: str, employee_code: str, reason: str = ""):
	if not _can_edit(user, frappe.session.user):
		frappe.throw(_("Only an admin of this person's team can change their employee code."), frappe.PermissionError)
	code = (employee_code or "").strip().upper()
	if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-_/]{1,29}", code):
		frappe.throw(_("Use letters, numbers and - _ / only (2–30 characters)."))
	# Lock the row we are about to change so a second admin can't slip the same code past the check.
	frappe.db.get_value("User", user, "name", for_update=True)
	if frappe.db.exists("User", {"employee_code": code, "name": ["!=", user]}):
		frappe.throw(_("Employee code {0} already belongs to someone else.").format(code))
	old = frappe.db.get_value("User", user, "employee_code")
	if old == code:
		return get_identity(user)
	frappe.db.set_value("User", user, "employee_code", code)
	if frappe.db.exists("LMS Onboarding Form", user):
		frappe.db.set_value("LMS Onboarding Form", user, "employee_code", code, update_modified=False)
	_log(user, "Employee code", old, code, reason)
	return get_identity(user)


@frappe.whitelist(methods=["POST"])
def change_email(user: str, new_email: str, reason: str = ""):
	"""Move an account to a new login email, keeping all progress (Frappe rename cascades every link)."""
	if not _can_edit(user, frappe.session.user):
		frappe.throw(_("Only an admin of this person's team can change their email."), frappe.PermissionError)
	new = (new_email or "").strip().lower()
	if not frappe.utils.validate_email_address(new):
		frappe.throw(_("Enter a valid email address."))
	if new == user.lower():
		return get_identity(user)
	if frappe.db.exists("User", new) or frappe.db.exists("User", {"email": new}):
		frappe.throw(_("{0} already has an account.").format(new))
	if user in ("Administrator", "Guest"):
		frappe.throw(_("This account can't be renamed."))

	# The account ID is the email: rename moves every Link to User (enrollments, progress, quizzes,
	# vivas, reporting lines, grants…) to the new ID.
	# Their open sessions still carry the old ID, and every write from those tabs would fail link
	# validation until they signed in again, so end them first.
	try:
		frappe.sessions.clear_sessions(user=user, force=True)
	except Exception:
		pass
	rename_doc("User", user, new, force=True, ignore_permissions=True, show_alert=False)
	frappe.db.set_value("User", new, "email", new)
	# Records named after the user keep their old name unless renamed too.
	for doctype in ("LMS Member", "LMS Onboarding Form"):
		if frappe.db.exists(doctype, user):
			rename_doc(doctype, user, new, force=True, ignore_permissions=True, show_alert=False)
	# Places that store the email as plain text.
	if frappe.db.table_exists("Sales OJT Certification Metric"):
		# They may also be somebody's training manager: that column holds an email, not a link, so
		# the rename leaves it behind and their trainees drop out of their reports.
		frappe.db.sql(
			"update `tabSales OJT Certification Metric` set training_manager=%s where training_manager=%s",
			(new, user),
		)
		for row in frappe.get_all("Sales OJT Certification Metric", {"email": user}, ["name", "batch_start"]):
			frappe.db.set_value(
				"Sales OJT Certification Metric",
				row.name,
				{"email": new, "row_key": f"{new}|{row.batch_start or ''}"},
				update_modified=False,
			)
	frappe.db.sql(f"update `tab{LOG}` set member=%s where member=%s", (new, user))
	for doctype, field in (("LMS Onboarding Form", "ac_email"), ("LMS Course Feedback", "learner_email")):
		if frappe.db.table_exists(doctype) and frappe.db.has_column(doctype, field):
			frappe.db.sql(f"update `tab{doctype}` set `{field}`=%s where `{field}`=%s", (new, user))
	_log(new, "Email", user, new, reason)
	access.clear_cache()
	return get_identity(new)
