# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Team & Access screen: who is in which team, their access role, reporting lines and extra views.

Super Admins manage everyone. A team Admin manages people in their own team(s) only, can put
people only into those teams, and cannot hand out Admin (a Super Admin does that). Extra view
grants are Super Admin only. Every rule is enforced here, not in the UI.
"""

import json

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from lms.lms import access
from lms.lms.doctype.lms_reporting_line.lms_reporting_line import end_reporting_line

ROLES = ["User", "Instructor", "Manager", "Admin"]
LINE_TYPES = ["Training Manager", "Performance Manager", "Floor Manager", "Line Manager", "Instructor", "Other"]


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def _ensure_admin():
	if frappe.session.user == "Guest" or not access.is_admin():
		frappe.throw(_("Only admins can manage team access."), frappe.PermissionError)


def _my_teams():
	"""Teams the current user may assign people to. None means every team (Super Admin)."""
	if access.is_super_admin():
		return None
	own = access.get_departments()
	if not own:
		return None  # Admin not yet placed in a team keeps full access (see access.py)
	parents = access._department_parents()
	teams = set()
	for department in own:
		teams |= access.expand_departments(department, parents)
	return teams


def _can_edit_member(user):
	teams = _my_teams()
	if teams is None:
		return True
	if not frappe.db.exists("LMS Member", user):
		return True  # adding someone new: allowed, but only into the admin's own teams
	if frappe.db.get_value("LMS Member", user, "access_role") == "Admin":
		return False  # only a Super Admin changes another admin
	current = set(
		frappe.get_all("LMS Member Department", filters={"parenttype": "LMS Member", "parent": user}, pluck="department")
	)
	return not current or bool(current & teams)


def _ensure_can_edit(user):
	if not _can_edit_member(user):
		frappe.throw(_("{0} is not in your team.").format(user), frappe.PermissionError)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def _super_admins():
	users = frappe.get_all(
		"Has Role",
		filters={"parenttype": "User", "role": "System Manager"},
		pluck="parent",
		distinct=True,
	)
	users = [u for u in users if u not in ("Administrator", "Guest")]
	if not users:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", users], "enabled": 1},
		fields=["name as user", "full_name", "user_image"],
		order_by="full_name asc",
	)


@frappe.whitelist()
def get_team_access():
	_ensure_admin()
	teams = _my_teams()
	super_admin = access.is_super_admin()

	departments = frappe.get_all(
		"LMS Department",
		filters={"is_active": 1},
		fields=["name", "parent_department", "description"],
		order_by="name asc",
	)
	rows = frappe.get_all(
		"LMS Member Department",
		filters={"parenttype": "LMS Member"},
		fields=["parent", "department", "is_primary"],
	)
	member_teams = {}
	for r in rows:
		member_teams.setdefault(r.parent, []).append({"department": r.department, "is_primary": r.is_primary})

	members = frappe.get_all(
		"LMS Member",
		fields=["name as user", "full_name", "access_role", "status"],
		order_by="full_name asc",
	)
	code_field = ["employee_code"] if frappe.db.has_column("User", "employee_code") else []
	user_rows = {
		u.name: u
		for u in frappe.get_all(
			"User", filters={"name": ["in", [m.user for m in members] or [""]]}, fields=["name", "user_image", *code_field]
		)
	}
	images = {name: u.user_image for name, u in user_rows.items()}

	lines = frappe.get_all(
		"LMS Reporting Line",
		filters={"status": "Active"},
		fields=["name", "member", "member_name", "manager", "manager_name", "line_type", "department", "from_date"],
		order_by="from_date desc",
	)
	managers_of = {}
	for line in lines:
		managers_of.setdefault(line.member, []).append(line)

	out = []
	for m in members:
		m_teams = member_teams.get(m.user, [])
		m.departments = sorted(m_teams, key=lambda d: (not d["is_primary"], d["department"]))
		m.user_image = images.get(m.user)
		m.employee_code = (user_rows.get(m.user) or {}).get("employee_code")
		m.managers = managers_of.get(m.user, [])
		in_scope = teams is None or not m_teams or any(d["department"] in teams for d in m_teams)
		m.can_edit = teams is None or (in_scope and m.access_role != "Admin")
		if in_scope:
			out.append(m)

	visible = {m.user for m in out}
	counts = {}
	for m in out:
		for d in m.departments:
			counts[d["department"]] = counts.get(d["department"], 0) + 1
	for d in departments:
		d.count = counts.get(d.name, 0)
		d.can_assign = teams is None or d.name in teams

	grants = []
	if super_admin:
		grants = frappe.get_all(
			"LMS View Grant",
			filters={"is_active": 1},
			fields=["name", "user", "user_name", "scope_type", "department", "include_sub_departments", "can_manage", "reason"],
			order_by="modified desc",
		)

	return {
		"me": {
			"user": frappe.session.user,
			"tier": access.get_tier_name(),
			"is_super_admin": super_admin,
			"teams": None if teams is None else sorted(teams),
		},
		"roles": ROLES if super_admin else [r for r in ROLES if r != "Admin"],
		"line_types": LINE_TYPES,
		"departments": departments,
		"members": out,
		"super_admins": _super_admins(),
		"lines": [line for line in lines if teams is None or line.member in visible],
		"grants": grants,
		"unassigned": sum(1 for m in out if m.status == "Active" and not m.managers),
	}


@frappe.whitelist()
def search_users(txt: str = ""):
	_ensure_admin()
	txt = (txt or "").strip()
	filters = {"enabled": 1, "name": ["not in", ["Guest", "Administrator"]]}
	or_filters = {"name": ["like", f"%{txt}%"], "full_name": ["like", f"%{txt}%"]} if txt else None
	users = frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		limit_page_length=12,
	)
	members = set(frappe.get_all("LMS Member", filters={"name": ["in", [u.name for u in users] or [""]]}, pluck="name"))
	for u in users:
		u.is_member = u.name in members
	return users


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def _as_list(value):
	if isinstance(value, str):
		value = json.loads(value or "[]")
	return list(value or [])


@frappe.whitelist(methods=["POST"])
def save_member(user: str, access_role: str, departments=None, primary: str | None = None):
	"""Create or update a person's access role and teams."""
	_ensure_admin()
	if not frappe.db.exists("User", user) or user in ("Guest", "Administrator"):
		frappe.throw(_("Pick a valid user."))
	if access_role not in ROLES:
		frappe.throw(_("Unknown access role."))
	if access_role == "Admin" and not access.is_super_admin():
		frappe.throw(_("Only a Super Admin can make someone an Admin."), frappe.PermissionError)
	if user == frappe.session.user and not access.is_super_admin():
		frappe.throw(_("You cannot change your own access."), frappe.PermissionError)
	_ensure_can_edit(user)

	departments = [d for d in dict.fromkeys(_as_list(departments)) if d]
	if not departments:
		frappe.throw(_("Pick at least one team."))
	teams = _my_teams()
	if teams is not None:
		outside = [d for d in departments if d not in teams]
		if outside:
			frappe.throw(_("You can only add people to your own teams (not {0}).").format(", ".join(outside)))
		if frappe.db.exists("LMS Member", user):
			# Keep teams the admin cannot see; they belong to another team's admin.
			other = [
				d
				for d in frappe.get_all(
					"LMS Member Department", filters={"parenttype": "LMS Member", "parent": user}, pluck="department"
				)
				if d not in teams
			]
			departments += [d for d in other if d not in departments]

	primary = primary if primary in departments else departments[0]
	doc = frappe.get_doc("LMS Member", user) if frappe.db.exists("LMS Member", user) else frappe.new_doc("LMS Member")
	doc.user = user
	doc.full_name = frappe.db.get_value("User", user, "full_name")
	doc.access_role = access_role
	designations = {r.department: r.designation for r in doc.get("departments") or []}
	doc.set("departments", [])
	for d in departments:
		doc.append("departments", {"department": d, "designation": designations.get(d), "is_primary": int(d == primary)})
	doc.save(ignore_permissions=True)
	access.clear_cache()
	return {"user": user}


@frappe.whitelist(methods=["POST"])
def add_reporting_line(member: str, manager: str, line_type: str, from_date: str | None = None, department: str | None = None):
	_ensure_admin()
	_ensure_can_edit(member)
	if line_type not in LINE_TYPES:
		frappe.throw(_("Unknown reporting type."))
	doc = frappe.new_doc("LMS Reporting Line")
	doc.update(
		{
			"member": member,
			"member_name": frappe.db.get_value("User", member, "full_name"),
			"manager": manager,
			"manager_name": frappe.db.get_value("User", manager, "full_name"),
			"line_type": line_type,
			"department": department or None,
			"from_date": getdate(from_date or nowdate()),
			"status": "Active",
		}
	)
	doc.insert(ignore_permissions=True)
	access.clear_cache()
	return doc.name


@frappe.whitelist()
def end_line(name: str, reason: str | None = None):
	_ensure_admin()
	doc = frappe.get_doc("LMS Reporting Line", name)
	_ensure_can_edit(doc.member)
	end_reporting_line(doc, reason or _("Ended from Team & Access"))
	access.clear_cache()


@frappe.whitelist(methods=["POST"])
def add_view_grant(user: str, department: str, can_manage: int = 0, reason: str | None = None):
	"""Let someone see (and optionally manage) a whole team they are not part of. Super Admin only."""
	if not access.is_super_admin():
		frappe.throw(_("Only a Super Admin can give extra team views."), frappe.PermissionError)
	doc = frappe.new_doc("LMS View Grant")
	doc.update(
		{
			"user": user,
			"user_name": frappe.db.get_value("User", user, "full_name"),
			"scope_type": "Department",
			"department": department,
			"include_sub_departments": 1,
			"can_manage": int(can_manage or 0),
			"is_active": 1,
			"reason": reason,
		}
	)
	doc.insert(ignore_permissions=True)
	access.clear_cache()
	return doc.name


@frappe.whitelist(methods=["POST"])
def revoke_view_grant(name: str):
	if not access.is_super_admin():
		frappe.throw(_("Only a Super Admin can remove team views."), frappe.PermissionError)
	frappe.db.set_value("LMS View Grant", name, "is_active", 0)
	access.clear_cache()


@frappe.whitelist(methods=["POST"])
def create_account(
	email: str,
	first_name: str,
	last_name: str | None = None,
	access_role: str = "User",
	departments=None,
	primary: str | None = None,
	employee_code: str | None = None,
):
	"""Create a learner account and put it straight into the admin's team.

	The person gets the standard welcome email with a link to set their password.
	"""
	_ensure_admin()
	email = (email or "").strip().lower()
	first_name = (first_name or "").strip()
	if not frappe.utils.validate_email_address(email) or not first_name:
		frappe.throw(_("Enter a valid email and first name."))
	if frappe.db.exists("User", email):
		frappe.throw(_("{0} already has an account. Search for them instead.").format(email))
	# Validate the team/role choice before creating anything.
	if access_role not in ROLES or (access_role == "Admin" and not access.is_super_admin()):
		frappe.throw(_("You cannot give this access role."), frappe.PermissionError)
	teams = _my_teams()
	chosen = [d for d in dict.fromkeys(_as_list(departments)) if d]
	if not chosen or (teams is not None and any(d not in teams for d in chosen)):
		frappe.throw(_("Pick one of your own teams."))

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": (last_name or "").strip(),
			"user_type": "Website User",
			"send_welcome_email": 1,
			"roles": [{"role": "LMS Student"}] if frappe.db.exists("Role", "LMS Student") else [],
		}
	)
	code = (employee_code or "").strip().upper()
	if code:
		if frappe.db.exists("User", {"employee_code": code}):
			frappe.throw(_("Employee code {0} already belongs to someone else.").format(code))
		user.employee_code = code  # otherwise a TEMP-#### placeholder is assigned
	user.insert(ignore_permissions=True)
	save_member(email, access_role, chosen, primary)
	return {"user": email}
