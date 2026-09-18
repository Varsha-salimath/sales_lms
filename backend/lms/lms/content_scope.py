# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Which team owns a course, batch or program, and who may see it.

Every course, batch and program has a `team` (LMS Department). A person sees:
  - everything, if they are a Super Admin;
  - content of their own teams (with sub-teams) and of teams they hold a view grant on;
  - anything they are enrolled in;
  - content with no team yet (shared/legacy).
Someone not placed in any team yet keeps the old behaviour and sees everything, so a new
joiner is never locked out before an admin assigns them.

New content defaults to the creator's main team, and people can only file content under
their own teams.
"""

import frappe
from frappe import _

from lms.lms import access

CONTENT_DOCTYPES = ("LMS Course", "LMS Batch", "LMS Program")
EVERYONE = None
DEFAULT_CRT_TEAM = "Retail Sales"


def _ready(doctype="LMS Course"):
	return frappe.db.has_column(doctype, "team")


def visible_teams(user=None):
	"""Set of teams whose content `user` sees, or None for everything."""
	user = user or frappe.session.user
	key = ("content_teams", user)
	cache = access._cache()
	if key in cache:
		return cache[key]

	result = EVERYONE
	if user != "Guest" and not access.is_super_admin(user):
		own = access.get_departments(user)
		grants = [
			g
			for g in access._active_grants(user)
			if g.scope_type in ("Department", "Everyone")
		]
		if any(g.scope_type == "Everyone" for g in grants):
			result = EVERYONE
		elif own or grants:
			parents = access._department_parents()
			teams = set()
			for department in own:
				teams |= access.expand_departments(department, parents)
			for g in grants:
				if g.department:
					teams |= access.expand_departments(g.department, parents, bool(g.include_sub_departments))
			result = teams
	cache[key] = result
	return result


def assignable_teams(user=None):
	"""Teams `user` may file new content under, or None for any team."""
	user = user or frappe.session.user
	if access.is_super_admin(user):
		return EVERYONE
	own = access.get_departments(user)
	managed = [g for g in access._active_grants(user) if g.can_manage and g.scope_type == "Department" and g.department]
	if not own and not managed:
		return EVERYONE if access.is_admin(user) else set()
	parents = access._department_parents()
	teams = set()
	for department in own:
		teams |= access.expand_departments(department, parents)
	# A team someone may manage (view grant with "Can Manage") is one they can add content to.
	for g in managed:
		teams |= access.expand_departments(g.department, parents, bool(g.include_sub_departments))
	return teams


def _enrolled(doctype, user):
	if doctype == "LMS Course":
		return set(frappe.get_all("LMS Enrollment", {"member": user}, pluck="course"))
	if doctype == "LMS Batch":
		return set(frappe.get_all("LMS Batch Enrollment", {"member": user}, pluck="batch"))
	if doctype == "LMS Program":
		return set(frappe.get_all("LMS Program Member", {"member": user}, pluck="parent"))
	return set()


def allowed_names(doctype, user=None):
	"""Names of `doctype` records visible to `user`, or None when unrestricted."""
	user = user or frappe.session.user
	teams = visible_teams(user)
	if teams is EVERYONE or not _ready(doctype):
		return EVERYONE
	names = set(
		frappe.get_all(
			doctype,
			or_filters=[[doctype, "team", "in", sorted(teams) or [""]], [doctype, "team", "is", "not set"]],
			pluck="name",
		)
	)
	return names | _enrolled(doctype, user)


def can_access(doctype, name, user=None):
	if not name:
		return True  # unsaved record: team rules apply on save (set_team)
	allowed = allowed_names(doctype, user)
	return allowed is EVERYONE or name in allowed


def scope_filters(doctype, filters, user=None):
	"""Narrow a frappe.get_all `filters` dict to what `user` may see (in place)."""
	allowed = allowed_names(doctype, user)
	if allowed is EVERYONE:
		return filters
	existing = filters.get("name")
	if isinstance(existing, (list, tuple)) and len(existing) == 2 and existing[0] == "in":
		allowed = allowed & set(existing[1] or [])
	elif isinstance(existing, str):
		allowed = allowed & {existing}
	filters["name"] = ["in", sorted(allowed) or [""]]
	return filters


# ---------------------------------------------------------------------------
# Document hooks
# ---------------------------------------------------------------------------


def set_team(doc, method=None):
	"""Default a new record's team to the creator's main team; keep people inside their teams."""
	if not _ready(doc.doctype) or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	user = frappe.session.user
	allowed = assignable_teams(user)
	if not doc.get("team"):
		primary = frappe.db.get_value(
			"LMS Member Department", {"parenttype": "LMS Member", "parent": user, "is_primary": 1}, "department"
		)
		if primary:
			doc.team = primary
		elif allowed:
			doc.team = sorted(allowed)[0]
	if allowed is not EVERYONE and doc.get("team") and doc.team not in allowed:
		if doc.is_new() or doc.has_value_changed("team"):
			frappe.throw(_("You can only add this to your own teams: {0}.").format(", ".join(sorted(allowed))))


def _query_conditions(doctype, user):
	allowed = allowed_names(doctype, user or frappe.session.user)
	if allowed is EVERYONE:
		return ""
	names = ", ".join(frappe.db.escape(n) for n in sorted(allowed)) or "''"
	return f"`tab{doctype}`.name in ({names})"


def course_query_conditions(user=None):
	return _query_conditions("LMS Course", user)


def batch_query_conditions(user=None):
	return _query_conditions("LMS Batch", user)


def program_query_conditions(user=None):
	return _query_conditions("LMS Program", user)


def has_course_permission(doc, ptype="read", user=None):
	"""Out-of-team courses are invisible; otherwise normal role permissions apply."""
	if ptype == "create" or doc.get("__islocal") or doc.is_new():
		return None
	if not can_access("LMS Course", doc.name, user or frappe.session.user):
		return False
	return None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_assignable_teams():
	"""Teams the current user can pick when creating a course, batch or program."""
	allowed = assignable_teams()
	teams = frappe.get_all("LMS Department", filters={"is_active": 1}, pluck="name", order_by="name asc")
	if allowed is not EVERYONE:
		teams = [t for t in teams if t in allowed]
	primary = frappe.db.get_value(
		"LMS Member Department",
		{"parenttype": "LMS Member", "parent": frappe.session.user, "is_primary": 1},
		"department",
	)
	return {"teams": teams, "default": primary if primary in teams else (teams[0] if len(teams) == 1 else None)}


def tag_existing_content():
	"""after_migrate: file the Sales CRT course under Retail Sales if it has no team yet."""
	if not _ready("LMS Course"):
		return
	from lms.lms.sales_journey import COURSE_SLUG

	if frappe.db.exists("LMS Course", COURSE_SLUG) and not frappe.db.get_value("LMS Course", COURSE_SLUG, "team"):
		if frappe.db.exists("LMS Department", DEFAULT_CRT_TEAM):
			frappe.db.set_value("LMS Course", COURSE_SLUG, "team", DEFAULT_CRT_TEAM, update_modified=False)
