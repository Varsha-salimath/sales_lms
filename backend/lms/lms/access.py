# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Central access model for the LMS.

Three separate questions, answered here and nowhere else:

1. Tier — what can this person do?  (User < Instructor < Manager < Admin < Super Admin)
2. Visibility — whose training data can they see?
     self + everyone below them through active reporting lines (recursive, any line type)
     + everyone covered by their active view grants.
   Admins also see every member of the departments they belong to (and sub-departments):
   a team admin, e.g. Retail Sales Training. Super Admins see everyone. An Admin with no
   department yet keeps the old see-everyone behaviour so nobody is locked out mid-setup.
3. Manageability — whom can they act on (assign training, request accounts)?
     Manager tier or above, and the person is in their reporting tree or in a view grant
     marked "Can Manage".

Ending a reporting line removes the old manager's view completely; the data stays.
"""

import frappe

USER, INSTRUCTOR, MANAGER, ADMIN, SUPER_ADMIN = 0, 1, 2, 3, 4
TIER_NAMES = {USER: "User", INSTRUCTOR: "Instructor", MANAGER: "Manager", ADMIN: "Admin", SUPER_ADMIN: "Super Admin"}

# Access role on LMS Member -> Frappe roles that grant it.
ACCESS_ROLE_FRAPPE_ROLES = {
	"User": [],
	"Instructor": ["Course Creator", "Batch Evaluator"],
	"Manager": ["LMS Manager"],
	"Admin": ["Moderator"],
}
TIER_ROLES = {"Course Creator", "Batch Evaluator", "LMS Manager", "Moderator"}


def _user(user=None):
	return user or frappe.session.user


def _cache():
	if not hasattr(frappe.local, "lms_access_cache"):
		frappe.local.lms_access_cache = {}
	return frappe.local.lms_access_cache


# ---------------------------------------------------------------------------
# Tier
# ---------------------------------------------------------------------------


def tier_from_roles(roles) -> int:
	roles = set(roles or [])
	if "System Manager" in roles or "Administrator" in roles:
		return SUPER_ADMIN
	if "Moderator" in roles:
		return ADMIN
	if "LMS Manager" in roles:
		return MANAGER
	if roles & {"Course Creator", "Batch Evaluator"}:
		return INSTRUCTOR
	return USER


def get_tier(user=None) -> int:
	user = _user(user)
	if user == "Administrator":
		return SUPER_ADMIN
	key = ("tier", user)
	cache = _cache()
	if key not in cache:
		cache[key] = tier_from_roles(frappe.get_roles(user))
	return cache[key]


def get_tier_name(user=None) -> str:
	return TIER_NAMES[get_tier(user)]


def is_super_admin(user=None) -> bool:
	return get_tier(user) >= SUPER_ADMIN


def is_admin(user=None) -> bool:
	return get_tier(user) >= ADMIN


def is_manager(user=None) -> bool:
	return get_tier(user) >= MANAGER


def bypasses_progression(user=None) -> bool:
	"""Instructors, managers (incl. Training Managers) and admins see every day and lesson unlocked;
	only learners go day by day, session by session."""
	user = _user(user)
	if user == "Guest":
		return False
	return get_tier(user) >= INSTRUCTOR or is_training_manager(user)


# ---------------------------------------------------------------------------
# Data access (kept small so the graph logic below stays pure and testable)
# ---------------------------------------------------------------------------


def _ready():
	return frappe.db.exists("DocType", "LMS Reporting Line")


def _active_lines():
	"""[(member, manager)] for every active reporting line."""
	if not _ready():
		return []
	return [
		(row.member, row.manager)
		for row in frappe.get_all(
			"LMS Reporting Line", filters={"status": "Active"}, fields=["member", "manager"]
		)
	]


def _active_grants(user):
	if not _ready():
		return []
	return frappe.get_all(
		"LMS View Grant",
		filters={"user": user, "is_active": 1},
		fields=["scope_type", "department", "include_sub_departments", "designation", "batch", "can_manage"],
	)


def _department_parents():
	"""{department: parent_department}"""
	return {
		row.name: row.parent_department
		for row in frappe.get_all("LMS Department", fields=["name", "parent_department"])
	}


def _members_in_departments(departments):
	if not departments:
		return set()
	return set(
		frappe.get_all(
			"LMS Member Department",
			filters={"parenttype": "LMS Member", "department": ["in", list(departments)]},
			pluck="parent",
		)
	)


def _members_with_designation(designation):
	return set(
		frappe.get_all(
			"LMS Member Department",
			filters={"parenttype": "LMS Member", "designation": designation},
			pluck="parent",
		)
	)


def _members_in_batch(batch):
	return set(frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member"))


# ---------------------------------------------------------------------------
# Pure graph helpers
# ---------------------------------------------------------------------------


def active_training_manager_lines():
	"""Active reporting edges where the manager role is Training Manager."""
	if not _ready():
		return []
	return [
		(row.member, row.manager)
		for row in frappe.get_all(
			"LMS Reporting Line",
			filters={"status": "Active", "line_type": "Training Manager"},
			fields=["member", "manager"],
		)
	]


def training_manager_tree(user=None) -> set:
	"""Learners under `user` through Training Manager reporting lines only."""
	user = _user(user)
	return reporting_tree(user, active_training_manager_lines())


def is_training_manager(user=None) -> bool:
	user = _user(user)
	if get_tier(user) >= MANAGER:
		return True
	return bool(training_manager_tree(user))


def reporting_tree(root, lines) -> set:
	"""Everyone below `root` through `lines` [(member, manager)], excluding root. Cycle-safe."""
	children = {}
	for member, manager in lines:
		children.setdefault(manager, set()).add(member)
	seen, frontier = set(), [root]
	while frontier:
		node = frontier.pop()
		for child in children.get(node, ()):
			if child not in seen and child != root:
				seen.add(child)
				frontier.append(child)
	return seen


def managers_above(member, lines) -> set:
	"""Everyone above `member` through `lines`. Used to block reporting cycles."""
	parents = {}
	for m, manager in lines:
		parents.setdefault(m, set()).add(manager)
	seen, frontier = set(), [member]
	while frontier:
		node = frontier.pop()
		for parent in parents.get(node, ()):
			if parent not in seen:
				seen.add(parent)
				frontier.append(parent)
	return seen


def expand_departments(department, parents, include_sub=True) -> set:
	"""A department plus (optionally) all of its descendants."""
	result = {department}
	if not include_sub:
		return result
	changed = True
	while changed:
		changed = False
		for dept, parent in parents.items():
			if parent in result and dept not in result:
				result.add(dept)
				changed = True
	return result


# ---------------------------------------------------------------------------
# Visibility & manageability
# ---------------------------------------------------------------------------

EVERYONE = None  # sentinel: no restriction


def _grant_members(grant, parents):
	if grant.scope_type == "Everyone":
		return EVERYONE
	if grant.scope_type == "Department" and grant.department:
		return _members_in_departments(
			expand_departments(grant.department, parents, bool(grant.include_sub_departments))
		)
	if grant.scope_type == "Designation" and grant.designation:
		return _members_with_designation(grant.designation)
	if grant.scope_type == "Batch" and grant.batch:
		return _members_in_batch(grant.batch)
	return set()


def _scope(user, manage_only):
	key = ("scope", user, manage_only)
	cache = _cache()
	if key in cache:
		return cache[key]

	tier = get_tier(user)
	if tier >= SUPER_ADMIN:
		cache[key] = EVERYONE
		return EVERYONE
	if manage_only and tier < MANAGER:
		cache[key] = set()
		return cache[key]

	members = reporting_tree(user, _active_lines())
	if not manage_only:
		members.add(user)

	parents = None
	if tier == ADMIN:
		own = get_departments(user)
		if not own:
			cache[key] = EVERYONE  # not placed in a team yet: legacy full access
			return EVERYONE
		parents = _department_parents()
		scope = set()
		for department in own:
			scope |= expand_departments(department, parents)
		members |= _members_in_departments(scope)

	for grant in _active_grants(user):
		if manage_only and not grant.can_manage:
			continue
		if parents is None:
			parents = _department_parents()
		covered = _grant_members(grant, parents)
		if covered is EVERYONE:
			cache[key] = EVERYONE
			return EVERYONE
		members |= covered

	cache[key] = members
	return members


def get_visible_members(user=None):
	"""Set of users whose data `user` may view, or None meaning everyone."""
	return _scope(_user(user), manage_only=False)


def get_manageable_members(user=None):
	"""Set of users `user` may act on, or None meaning everyone."""
	return _scope(_user(user), manage_only=True)


def can_view_member(member, user=None) -> bool:
	scope = get_visible_members(user)
	return scope is EVERYONE or member in scope


def can_manage_member(member, user=None) -> bool:
	scope = get_manageable_members(user)
	return scope is EVERYONE or member in scope


def member_filter(user=None):
	"""Frappe filter value for a `member` column: None (no filter) or ["in", [...]]."""
	scope = get_visible_members(user)
	if scope is EVERYONE:
		return None
	return ["in", sorted(scope) or [""]]


def get_departments(user=None) -> list:
	"""Departments a person belongs to (for team admin scope and 'assign only from own department')."""
	user = _user(user)
	if not frappe.db.exists("DocType", "LMS Member Department"):
		return []
	return frappe.get_all(
		"LMS Member Department", filters={"parenttype": "LMS Member", "parent": user}, pluck="department"
	)


def can_view_department(department, user=None) -> bool:
	"""Whole-department view: Super Admin, that department's Admin, or a Department view grant."""
	user = _user(user)
	tier = get_tier(user)
	if tier >= SUPER_ADMIN:
		return True
	parents = _department_parents() if frappe.db.exists("DocType", "LMS Department") else {}
	if tier == ADMIN:
		own = get_departments(user)
		if not own:
			return True
		if any(department in expand_departments(d, parents) for d in own):
			return True
	for grant in _active_grants(user):
		if grant.scope_type == "Everyone":
			return True
		if grant.scope_type == "Department" and grant.department and department in expand_departments(
			grant.department, parents, bool(grant.include_sub_departments)
		):
			return True
	return False


def filter_rows_by_email(rows, user=None, field="email"):
	"""Keep rows whose person (by email/user id) is visible to `user`."""
	scope = get_visible_members(user)
	if scope is EVERYONE:
		return rows
	scope = {s.lower() for s in scope}
	return [r for r in rows if (r.get(field) or "").lower() in scope]


def clear_cache():
	if hasattr(frappe.local, "lms_access_cache"):
		frappe.local.lms_access_cache = {}


@frappe.whitelist()
def get_my_access():
	"""Summary for the SPA: tier and how wide the person's view is."""
	user = frappe.session.user
	visible = get_visible_members(user)
	manageable = get_manageable_members(user)
	return {
		"tier": get_tier_name(user),
		"is_super_admin": is_super_admin(user),
		"is_admin": is_admin(user),
		"is_manager": is_manager(user),
		"sees_everyone": visible is EVERYONE,
		"visible_count": None if visible is EVERYONE else len(visible),
		"manageable_count": None if manageable is EVERYONE else len(manageable),
		"departments": get_departments(user),
	}
