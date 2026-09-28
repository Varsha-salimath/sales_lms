# Ops Checklist (Staff Onboarding/Compliance Guide) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 4 existing Sales Training roles (Sales Training Team, Sales Trainee Manager, Sales Training Finance, Sales Training Leadership) a role-scoped "Ops Checklist" — a skippable first-login tour plus a persistent, always-visible sidebar badge and full-page live checklist of overdue SOP items — computed entirely from data the app already tracks.

**Architecture:** One new minimal DocType (`Ops Checklist Tour State`) to remember per-user tour-skip state; one new backend module (`ops_checklist.py`) that composes existing read APIs (`trainee_cohort_stats`, `trainee_dashboard`, `Weekly Payroll Cycle`) into a role-scoped item list, computed fresh on every call (never cached/stored); one new Vue page + a small sidebar badge, both `genius-*` styled to match the rest of the staff surface.

**Tech Stack:** Frappe (Python ≥3.10) backend, MariaDB. Vue 3 + `frappe-ui` (`createResource`/`call`) frontend, vue-router 4. Test runner: `bench run-tests` (backend only — this repo has no frontend test framework; frontend tasks are verified by build + manual browser check, matching existing project practice).

**Spec:** `docs/superpowers/specs/2026-09-28-ops-checklist-onboarding-design.md`

## Global Constraints

- Staff-only. No trainee-facing surface, no new Frappe Role, no login flow changes.
- No new pre-join/offer-letter/DOJ/vendor-billing-reconciliation tracking of any kind — explicit non-goal (spec §1, §8).
- Visual language is `genius-*` (staff/admin), never `il-*` (learner-facing) — matches `TraineeList.vue`, `TraineeAttendanceHistory.vue`, `WeeklyPayrollCycle.vue`.
- Feature name in-code/UI is "Ops Checklist" — never call it "onboarding" in user-facing copy or route names, to avoid collision with the existing learner-facing `SalesOnboardingHome.vue`.
- Tour skip is **permanent per user** and applies only to the static tour banner. The live checklist below it is never dismissible/snoozable — it clears an item only when the underlying task is actually done.
- All access checks follow this codebase's established pattern: enforced in a Python helper function inside the whitelisted method (e.g. `_ensure_cohort_stats_access`), not relied upon solely via DocType permissions or frontend route guards. Reuse `lms.lms.trainee_scope.ORG_WIDE_TRAINEE_ROLES` and `lms.lms.access.is_admin()` rather than re-deriving role sets.
- One deviation from the spec's exact wording, made for this plan and flagged to the user: the Finance checklist item is "payroll cycle still open" (derived from `Weekly Payroll Cycle.status`), not "reconciliation export not yet run" — there is no existing field tracking whether that export was run, and adding one would be new tracking infrastructure the spec explicitly rules out. An open, un-closed cycle already implies the reconciliation step hasn't been completed.

## Review Focus

- A logged-in user who holds **none** of the 4 Sales Training roles (and isn't Admin/System Manager) hits `/ops-checklist` directly by URL, or calls the backend API directly — must be redirected/blocked, not shown a blank or erroring page. (Task 2, Task 4)
- A **Sales Trainee Manager with zero trainees** in their own reporting tree (a brand-new manager, day one) — the checklist must render an empty/"all caught up" state, never a crash or an unhandled-exception page. (Task 2, Task 3)
- A user who is **both Admin/System Manager and holds a scoped role** (e.g. also has `Sales Trainee Manager`) must see the org-wide item set, not get incorrectly narrowed to their own (possibly empty) reporting tree. (Task 2)
- The **skip-tour endpoint** called with no prior state row (first-ever visit) and called **twice in a row** (double-click, or revisiting an already-skipped tour) — neither call may error. (Task 1)
- The **payroll-deadline countdown** computed near a **month boundary** (today is the 26th–31st, after this month's 25th has passed) must roll over to next month's 25th with a valid, non-negative day count — not error or return a nonsensical value. (Task 2)

---

## File Structure

- `backend/lms/lms/doctype/ops_checklist_tour_state/` (new) — minimal DocType: `__init__.py`, `ops_checklist_tour_state.json`, `ops_checklist_tour_state.py`. One row per user; presence of `skipped_on` = tour dismissed.
- `backend/lms/lms/ops_checklist.py` (new) — all backend logic: tour-state get/skip, and the role-scoped `get_ops_checklist()` aggregator. One file, mirrors the single-file-per-feature pattern already used by `trainee_dashboard.py`/`trainee_cohort_stats.py`.
- `backend/lms/lms/test_ops_checklist.py` (new) — tests for both the tour-state endpoints and the aggregator, using the existing `trainee_test_utils.make_user`/`make_trainee`/`run_as` fixtures.
- `frontend/src/pages/Sales/OpsChecklist.vue` (new) — the full checklist page (tour banner + live list), `genius-*` styled.
- `frontend/src/components/Sidebar/AppSidebar.vue` (modify) — add a small pending-count badge next to the new nav entry.
- `frontend/src/utils/index.js` (modify) — add the "Ops Checklist" sidebar link entry with its role condition, next to the existing `Trainees`/`Payroll cycles` entries (~line 655).
- `frontend/src/router.js` (modify) — new `/ops-checklist` route, added to the existing `staffOnlyRoutes`/`salesTrainingRoutes` arrays (~lines 536, 577).

## Task 1: `Ops Checklist Tour State` DocType + skip/get endpoints

**Files:**
- Create: `backend/lms/lms/doctype/ops_checklist_tour_state/__init__.py`
- Create: `backend/lms/lms/doctype/ops_checklist_tour_state/ops_checklist_tour_state.json`
- Create: `backend/lms/lms/doctype/ops_checklist_tour_state/ops_checklist_tour_state.py`
- Create: `backend/lms/lms/ops_checklist.py`
- Test: `backend/lms/lms/test_ops_checklist.py`

**Interfaces:**
- Produces: `lms.lms.ops_checklist.get_ops_checklist_tour_state()` → `{"skipped": bool, "skipped_on": str | None}`. `lms.lms.ops_checklist.skip_ops_checklist_tour()` → `{"skipped": True}`. Both whitelisted, operate on `frappe.session.user` only, throw `frappe.PermissionError` for `Guest`.

- [ ] **Step 1: Write the failing tests**

Create `backend/lms/lms/test_ops_checklist.py`:

```python
"""Ops Checklist: per-user tour-skip state, and the role-scoped live checklist."""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import getdate

from lms.lms.ops_checklist import get_ops_checklist_tour_state, skip_ops_checklist_tour
from lms.lms.trainee_test_utils import make_user, run_as


class TestOpsChecklistTourState(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.user = make_user("occ-tour", "Sales Training Team")

	def test_new_user_tour_is_not_skipped(self):
		run_as(self, self.user)
		state = get_ops_checklist_tour_state()
		self.assertEqual(state["skipped"], False)
		self.assertIsNone(state["skipped_on"])

	def test_skip_tour_marks_it_skipped(self):
		run_as(self, self.user)
		skip_ops_checklist_tour()
		state = get_ops_checklist_tour_state()
		self.assertEqual(state["skipped"], True)
		self.assertIsNotNone(state["skipped_on"])

	def test_skip_tour_is_idempotent(self):
		run_as(self, self.user)
		skip_ops_checklist_tour()
		# second call must not raise, and must not create a duplicate row
		skip_ops_checklist_tour()
		count = frappe.db.count("Ops Checklist Tour State", {"user": self.user})
		self.assertEqual(count, 1)

	def test_guest_is_denied(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		self.assertRaises(frappe.PermissionError, get_ops_checklist_tour_state)
		self.assertRaises(frappe.PermissionError, skip_ops_checklist_tour)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_ops_checklist -v`
Expected: FAIL / ImportError — `lms.lms.ops_checklist` doesn't exist yet, and the `Ops Checklist Tour State` DocType doesn't exist.

- [ ] **Step 3: Create the DocType**

Create `backend/lms/lms/doctype/ops_checklist_tour_state/__init__.py` (empty file).

Create `backend/lms/lms/doctype/ops_checklist_tour_state/ops_checklist_tour_state.json`:

```json
{
 "actions": [],
 "creation": "2026-09-28 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["user", "skipped_on"],
 "fields": [
  {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1, "unique": 1, "in_list_view": 1},
  {"fieldname": "skipped_on", "fieldtype": "Datetime", "label": "Skipped On"}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-28 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Ops Checklist Tour State",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1, "email": 1, "share": 1},
  {"role": "Sales Training Team", "read": 1, "report": 1},
  {"role": "Sales Trainee Manager", "read": 1, "report": 1},
  {"role": "Sales Training Finance", "read": 1, "report": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": [],
 "title_field": "user",
 "autoname": "field:user",
 "naming_rule": "By fieldname",
 "track_changes": 0
}
```

Create `backend/lms/lms/doctype/ops_checklist_tour_state/ops_checklist_tour_state.py`:

```python
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class OpsChecklistTourState(Document):
	pass
```

- [ ] **Step 4: Implement the tour-state endpoints**

Create `backend/lms/lms/ops_checklist.py`:

```python
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


def _ensure_logged_in():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


@frappe.whitelist()
def get_ops_checklist_tour_state():
	_ensure_logged_in()
	skipped_on = frappe.db.get_value("Ops Checklist Tour State", frappe.session.user, "skipped_on")
	return {"skipped": bool(skipped_on), "skipped_on": skipped_on}


@frappe.whitelist()
def skip_ops_checklist_tour():
	_ensure_logged_in()
	if frappe.db.exists("Ops Checklist Tour State", frappe.session.user):
		frappe.db.set_value("Ops Checklist Tour State", frappe.session.user, "skipped_on", now_datetime())
	else:
		frappe.get_doc(
			{"doctype": "Ops Checklist Tour State", "user": frappe.session.user, "skipped_on": now_datetime()}
		).insert(ignore_permissions=True)
	return {"skipped": True}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_ops_checklist -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/ops_checklist_tour_state backend/lms/lms/ops_checklist.py backend/lms/lms/test_ops_checklist.py
git commit -m "feat(sales): add Ops Checklist tour-skip state and endpoints"
```

## Task 2: Role-scoped live checklist aggregator

**Files:**
- Modify: `backend/lms/lms/ops_checklist.py`
- Modify: `backend/lms/lms/test_ops_checklist.py`

**Interfaces:**
- Consumes: `lms.lms.trainee_cohort_stats.list_missing_attendance(attendance_date, cohort=None)` (existing), `lms.lms.trainee_dashboard.get_dashboard_summary()` (existing), `lms.lms.trainee_scope.ORG_WIDE_TRAINEE_ROLES` (existing set: `{"Sales Training Team", "Sales Training Finance", "Sales Training Leadership"}`), `lms.lms.access.is_admin()` / `access.reporting_tree(user, lines)` (existing).
- Produces: `lms.lms.ops_checklist.get_ops_checklist()` → `{"items": [{"key": str, "title": str, "action_route": {"name": str}}], "summary": dict | None}`. Consumed by Task 3 (page) and Task 4 (sidebar badge, via `len(items)`).

- [ ] **Step 1: Write the failing tests**

Append to `backend/lms/lms/test_ops_checklist.py`:

```python
from datetime import date

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.ops_checklist import get_ops_checklist
from lms.lms.trainee_test_utils import make_trainee


class TestOpsChecklistAggregator(UnitTestCase):
	def setUp(self):
		super().setUp()
		tag = frappe.generate_hash(length=6)
		self.today = date.today().isoformat()
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"OCC-{tag}", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		self.manager = make_user("occ-manager", "Sales Trainee Manager")
		self.finance_user = make_user("occ-finance", "Sales Training Finance")
		self.leadership_user = make_user("occ-lead", "Sales Training Leadership")
		self.team_user = make_user("occ-team", "Sales Training Team")
		self.trainee = make_trainee(f"OCC Mine {tag}", assigned_sales_manager=self.manager, cohort=self.cohort.name)

	def test_team_role_sees_missing_attendance_for_the_cohort(self):
		run_as(self, self.team_user)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_manager_with_no_trainees_gets_no_attendance_items(self):
		other_manager = make_user("occ-manager-empty", "Sales Trainee Manager")
		run_as(self, other_manager)
		result = get_ops_checklist()
		self.assertEqual(result["items"], [])

	def test_manager_is_scoped_to_their_own_trainees(self):
		run_as(self, self.manager)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_marking_attendance_clears_the_item(self):
		mark(self.trainee.name, self.today, "Present")
		run_as(self, self.manager)
		result = get_ops_checklist()
		self.assertFalse(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_finance_role_sees_open_cycle_item(self):
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"cohort": self.cohort.name,
				"status": "Preparing",
			}
		).insert(ignore_permissions=True)
		run_as(self, self.finance_user)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"cycle:{cycle.name}" for item in result["items"]))

	def test_leadership_role_gets_summary_not_action_items(self):
		run_as(self, self.leadership_user)
		result = get_ops_checklist()
		self.assertEqual(result["items"], [])
		self.assertIsNotNone(result["summary"])
		self.assertIn("total", result["summary"])

	def test_admin_with_scoped_role_sees_org_wide_view_not_empty_scope(self):
		admin_with_manager_role = make_user("occ-admin-manager", "Sales Trainee Manager")
		frappe.get_doc("User", admin_with_manager_role).add_roles("System Manager")
		run_as(self, admin_with_manager_role)
		result = get_ops_checklist()
		self.assertTrue(any(item["key"] == f"attendance:{self.cohort.name}" for item in result["items"]))

	def test_user_without_any_sales_role_is_denied(self):
		bystander = make_user("occ-bystander")
		run_as(self, bystander)
		self.assertRaises(frappe.PermissionError, get_ops_checklist)

	def test_payroll_deadline_item_present_and_well_formed(self):
		run_as(self, self.team_user)
		result = get_ops_checklist()
		deadline_items = [item for item in result["items"] if item["key"] == "payroll-deadline"]
		self.assertEqual(len(deadline_items), 1)
		self.assertIn("day", deadline_items[0]["title"])


class TestPayrollDeadlineMath(UnitTestCase):
	"""Direct tests of the date math, independent of "today" — the aggregator test
	above only proves an item exists, not that month-boundary rollover is correct."""

	def test_deadline_on_or_before_the_25th_is_this_month(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-10"))[0]
		self.assertIn("2026-09-25", item["title"])

	def test_deadline_after_the_25th_rolls_over_to_next_month(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-28"))[0]
		self.assertIn("2026-10-25", item["title"])
		self.assertIn("27 day(s) left", item["title"])

	def test_deadline_on_the_25th_itself_is_zero_days_left(self):
		from lms.lms.ops_checklist import _payroll_deadline_item

		item = _payroll_deadline_item(getdate("2026-09-25"))[0]
		self.assertIn("0 day(s) left", item["title"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_ops_checklist -v`
Expected: FAIL — `get_ops_checklist` not defined.

- [ ] **Step 3: Implement the aggregator**

Append to `backend/lms/lms/ops_checklist.py` (add these imports to the top of the file alongside the existing ones):

```python
from frappe.utils import add_months, date_diff, getdate

from lms.lms import access
from lms.lms.trainee_cohort_stats import list_missing_attendance
from lms.lms.trainee_dashboard import get_dashboard_summary
from lms.lms.trainee_scope import ORG_WIDE_TRAINEE_ROLES

PAYROLL_EXPORT_DAY = 25
SALES_TRAINING_ROLES = ORG_WIDE_TRAINEE_ROLES | {"Sales Trainee Manager"}
```

Then append these functions to the end of the file:

```python
def _safe_section(label, fn):
	"""Each checklist section is independent — one bad query must not blank the
	whole page for every other section (spec §4)."""
	try:
		return fn()
	except Exception:
		frappe.log_error(title=f"Ops Checklist: {label} section failed")
		return [{"key": f"error:{label}", "title": f"Couldn't load {label} — try reloading.", "action_route": None}]


@frappe.whitelist()
def get_ops_checklist():
	_ensure_ops_checklist_access()
	roles = set(frappe.get_roles())
	items = []

	org_wide_view = access.is_admin() or "Sales Training Team" in roles
	if org_wide_view:
		items += _safe_section("attendance", _team_attendance_items)
	elif "Sales Trainee Manager" in roles:
		items += _safe_section("attendance", lambda: _manager_attendance_items(frappe.session.user))

	if org_wide_view:
		items += _safe_section("payroll deadline", _payroll_deadline_item)

	if "Sales Training Finance" in roles:
		items += _safe_section("payroll cycles", _finance_items)

	summary = None
	if "Sales Training Leadership" in roles:
		try:
			summary = get_dashboard_summary()
		except Exception:
			frappe.log_error(title="Ops Checklist: leadership summary section failed")
			summary = None

	return {"items": items, "summary": summary}


def _ensure_ops_checklist_access():
	_ensure_logged_in()
	roles = set(frappe.get_roles())
	if not (access.is_admin() or roles & SALES_TRAINING_ROLES):
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


def _team_attendance_items():
	today = getdate()
	items = []
	for cohort_name in frappe.get_all("Sales Trainee Cohort", pluck="name"):
		missing = list_missing_attendance(str(today), cohort=cohort_name)
		if missing:
			items.append(
				{
					"key": f"attendance:{cohort_name}",
					"title": f"{len(missing)} trainee(s) in cohort {cohort_name} have no attendance marked for {today}",
					"action_route": {"name": "TraineeAttendance"},
				}
			)
	return items


def _manager_attendance_items(user):
	today = getdate()
	lines = [
		(row.member, row.manager)
		for row in frappe.get_all("LMS Reporting Line", filters={"status": "Active"}, fields=["member", "manager"])
	]
	visible_users = access.reporting_tree(user, lines) | {user}
	my_trainees = frappe.get_all(
		"Sales Trainee",
		filters={"training_status": "In Training", "assigned_sales_manager": ["in", list(visible_users)]},
		fields=["name", "cohort"],
	)
	items = []
	cohorts = {t.cohort for t in my_trainees if t.cohort}
	for cohort_name in cohorts:
		mine_in_cohort = {t.name for t in my_trainees if t.cohort == cohort_name}
		missing = set(list_missing_attendance(str(today), cohort=cohort_name)) & mine_in_cohort
		if missing:
			items.append(
				{
					"key": f"attendance:{cohort_name}",
					"title": f"{len(missing)} of your trainee(s) in cohort {cohort_name} have no attendance marked for {today}",
					"action_route": {"name": "TraineeAttendance"},
				}
			)
	return items


def _payroll_deadline_item(today=None):
	today = today or getdate()
	if today.day <= PAYROLL_EXPORT_DAY:
		next_deadline = today.replace(day=PAYROLL_EXPORT_DAY)
	else:
		next_deadline = add_months(today.replace(day=1), 1).replace(day=PAYROLL_EXPORT_DAY)
	days_left = date_diff(next_deadline, today)
	return [
		{
			"key": "payroll-deadline",
			"title": f"Vendor payroll data due {next_deadline} ({days_left} day(s) left) — confirm all open payroll cycles are ready to export",
			"action_route": {"name": "WeeklyPayrollCycle"},
		}
	]


def _finance_items():
	items = []
	open_cycles = frappe.get_all(
		"Weekly Payroll Cycle", filters={"status": ["!=", "Closed"]}, fields=["name", "status", "week_end"]
	)
	for cycle in open_cycles:
		items.append(
			{
				"key": f"cycle:{cycle.name}",
				"title": f'Payroll cycle {cycle.name} (week ending {cycle.week_end}) is still "{cycle.status}" — move it forward before month-end close',
				"action_route": {"name": "WeeklyPayrollCycle"},
			}
		)
	return items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_ops_checklist -v`
Expected: PASS (16 tests total across all three test classes)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/ops_checklist.py backend/lms/lms/test_ops_checklist.py
git commit -m "feat(sales): add role-scoped Ops Checklist aggregator"
```

## Task 3: `OpsChecklist.vue` frontend page

**Files:**
- Create: `frontend/src/pages/Sales/OpsChecklist.vue`

**Interfaces:**
- Consumes: `lms.lms.ops_checklist.get_ops_checklist_tour_state`, `lms.lms.ops_checklist.skip_ops_checklist_tour`, `lms.lms.ops_checklist.get_ops_checklist` (all via `frappe-ui`'s `call`/`createResource`, matching the pattern in `WeeklyPayrollCycle.vue`).
- Produces: a mounted route component consumed by Task 4's router entry.

- [ ] **Step 1: Check the existing call pattern this page must match**

Read `frontend/src/pages/Sales/WeeklyPayrollCycle.vue`'s top `<script setup>` block (the `createResource`/`call` usage) before writing this file, so the new page's data-fetching matches the established convention exactly rather than inventing a new one.

- [ ] **Step 2: Write the page**

Create `frontend/src/pages/Sales/OpsChecklist.vue`:

```vue
<template>
	<div class="genius-page mx-auto max-w-3xl p-6">
		<h1 class="genius-page-title text-2xl font-semibold">Ops Checklist</h1>

		<div v-if="tourState.data && !tourState.data.skipped" class="genius-card mt-4 p-4">
			<p class="text-p-base">
				{{ tourCopy }}
			</p>
			<button type="button" class="genius-btn-secondary mt-3" @click="skipTour">
				Skip
			</button>
		</div>

		<div v-if="checklist.loading" class="mt-6 text-p-base text-gray-500">Loading…</div>

		<div v-else-if="checklist.error" class="genius-card mt-6 p-4 text-p-base text-red-600">
			Couldn't load your checklist. Try reloading the page.
		</div>

		<div v-else class="mt-6 flex flex-col gap-3">
			<div v-if="items.length === 0" class="genius-card p-4 text-p-base text-gray-600">
				Nothing pending — you're all caught up.
			</div>
			<!-- A section that failed server-side (spec §4) comes back as a plain item with
			     action_route: null — render it as a static error card, not a broken router-link. -->
			<template v-for="item in pendingItems" :key="item.key">
				<router-link
					:to="item.action_route"
					class="genius-card flex items-center justify-between p-4"
				>
					<span class="text-p-base">{{ item.title }}</span>
				</router-link>
			</template>
			<div
				v-for="item in erroredItems"
				:key="item.key"
				class="genius-card p-4 text-p-base text-red-600"
			>
				{{ item.title }}
			</div>

			<div v-if="summary" class="genius-card mt-2 p-4">
				<h2 class="text-lg font-medium">Trainee status summary</h2>
				<dl class="mt-2 grid grid-cols-2 gap-2 text-p-sm">
					<template v-for="(value, key) in displaySummary" :key="key">
						<dt class="text-gray-500">{{ key }}</dt>
						<dd class="font-medium">{{ value }}</dd>
					</template>
				</dl>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, call } from 'frappe-ui'
import { usersStore } from '@/stores/user'

const { userResource } = usersStore()

const tourState = createResource({
	url: 'lms.lms.ops_checklist.get_ops_checklist_tour_state',
	auto: true,
})

const checklist = createResource({
	url: 'lms.lms.ops_checklist.get_ops_checklist',
	auto: true,
})

const items = computed(() => checklist.data?.items || [])
const pendingItems = computed(() => items.value.filter((item) => item.action_route))
const erroredItems = computed(() => items.value.filter((item) => !item.action_route))
const summary = computed(() => checklist.data?.summary || null)
const displaySummary = computed(() => {
	if (!summary.value) return {}
	const { total, ...rest } = summary.value
	return { total, ...rest }
})

const tourCopy = computed(() => {
	const roles = userResource.data?.roles || []
	if (roles.includes('Sales Training Finance')) {
		return "This is your Ops Checklist — it lists payroll cycles that still need to be closed before month-end, so you never miss the vendor's invoicing window."
	}
	if (roles.includes('Sales Trainee Manager')) {
		return 'This is your Ops Checklist — it lists your own trainees with unmarked attendance for today, so you never fall behind on OJT tracking.'
	}
	if (roles.includes('Sales Training Leadership')) {
		return 'This is your Ops Checklist — a read-only summary of trainee status across the program.'
	}
	return 'This is your Ops Checklist — it lists cohorts with unmarked attendance, un-cleared trainees, and the next payroll-export deadline, so nothing in the SOP slips.'
})

function skipTour() {
	call('lms.lms.ops_checklist.skip_ops_checklist_tour').then(() => {
		tourState.reload()
	})
}
</script>
```

- [ ] **Step 3: Build the frontend to catch syntax/import errors**

Run: `cd frontend && yarn build`
Expected: build succeeds with no errors referencing `OpsChecklist.vue`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Sales/OpsChecklist.vue
git commit -m "feat(sales): add Ops Checklist page"
```

## Task 4: Route, sidebar link, and pending-count badge

**Files:**
- Modify: `frontend/src/router.js` (~lines 113-117 for the route; ~546, ~577 for the two role-gate arrays)
- Modify: `frontend/src/utils/index.js` (~line 655, alongside the existing `Trainees`/`Payroll cycles` sidebar entries)
- Modify: `frontend/src/components/Sidebar/AppSidebar.vue`

**Interfaces:**
- Consumes: Task 2's `lms.lms.ops_checklist.get_ops_checklist` (for the badge count), Task 3's `OpsChecklist.vue`.

- [ ] **Step 1: Add the route**

In `frontend/src/router.js`, add immediately after the existing `WeeklyPayrollCycle` route (after line 117):

```javascript
	{
		path: '/sales-trainees/ops-checklist',
		name: 'OpsChecklist',
		component: () => import('@/pages/Sales/OpsChecklist.vue'),
	},
```

Add `'OpsChecklist'` to the `staffOnlyRoutes` array (the one starting `'AnalyticsDashboard', 'AdminDashboard', ...` around line 546) and to the `salesTrainingRoutes` array (around line 577), in both cases alongside the existing `'WeeklyPayrollCycle'` entry — this route must be gated exactly the same way as the other 4 Sales Training screens.

- [ ] **Step 2: Add the sidebar link**

In `frontend/src/utils/index.js`, add this entry to the `items` array in `getSidebarItems`, immediately after the existing `'Payroll cycles'` entry (~line 655):

```javascript
				{
					label: 'Ops Checklist',
					icon: 'ListChecks',
					to: 'OpsChecklist',
					activeFor: ['OpsChecklist'],
					condition: () => {
						const tier = userResource?.data?.access_tier
						const roles = userResource?.data?.roles || []
						return !forMobile && (
							['Admin', 'Super Admin'].includes(tier) ||
							['Sales Training Team', 'Sales Trainee Manager', 'Sales Training Finance', 'Sales Training Leadership'].some((r) => roles.includes(r))
						)
					},
				},
```

(`ListChecks` is an existing `lucide-vue-next` icon name, same import mechanism already used for `Wallet`/`BarChart2`/etc. in this file — no new import needed since `AppSidebar.vue` already does `import * as icons from 'lucide-vue-next'`.)

- [ ] **Step 3: Add the pending-count badge**

In `frontend/src/components/Sidebar/AppSidebar.vue`, add a resource fetching the count and wire it into the existing item-count mechanism already used for `Notifications` (see `updateUnreadCount`, lines 411-419). Add near the other `createResource` calls (after `streakInfo`, ~line 409):

```javascript
const opsChecklistCount = createResource({
	url: 'lms.lms.ops_checklist.get_ops_checklist',
	auto: !!user,
	cache: ['ops-checklist-count', user],
	onSuccess(data) {
		updateOpsChecklistBadge(data?.items?.length || 0)
	},
})

const updateOpsChecklistBadge = (count) => {
	sidebarLinks.value?.forEach((link) => {
		link.items.forEach((item) => {
			if (item.label === 'Ops Checklist') {
				item.count = count
			}
		})
	})
}
```

Call `updateOpsChecklistBadge(opsChecklistCount.data?.items?.length || 0)` inside `updateSidebarLinks` (alongside the existing `updateUnreadCount()` call at line 507), guarded the same way — if a user has no Sales Training role, `get_ops_checklist` will throw a `PermissionError`, so wrap the resource call defensively: add `onError() {}` to `opsChecklistCount` so a denied non-Sales-Training user simply never gets a badge, instead of a console error. `SidebarLink.vue:33-41` already renders `link.count` as a pill whenever it's truthy (confirmed — the exact mechanism the `Notifications` item already uses), so no change to `SidebarLink.vue` is needed; only `AppSidebar.vue` and the new sidebar-link entry need touching.

- [ ] **Step 4: Build and manually verify in the browser**

Run: `cd frontend && yarn build`
Expected: build succeeds.

Then, with a local dev site running (`~/.frappe-bench-cli/bin/bench serve --port 8000`), log in as a user holding `Sales Training Team` and confirm:
- The "Ops Checklist" sidebar link appears with a count badge.
- Clicking it opens `/sales-trainees/ops-checklist` and shows the tour banner + live items.
- Clicking "Skip" hides the tour banner and it stays hidden on reload.
- Logging in as a user with no Sales Training role does not show the link, and navigating to the URL directly redirects away (matching the existing `staffOnlyRoutes` behavior for e.g. `WeeklyPayrollCycle`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router.js frontend/src/utils/index.js frontend/src/components/Sidebar/AppSidebar.vue
git commit -m "feat(sales): wire Ops Checklist into router, sidebar nav, and badge"
```

## Task 5: Dogfooding — seed realistic data and verify all 4 roles

**Files:**
- Create: `backend/lms/patches/ops_checklist_seed_demo_data.py` (throwaway seed script — not a real Frappe patch registered in `patches.txt`, just a runnable one-off via `bench execute`, matching how demo data was seeded for the 2026-09-28 live-demo rehearsal per the vault session log)

**Interfaces:**
- Consumes: `Sales Trainee`, `Sales Trainee Cohort`, `Weekly Payroll Cycle` (existing doctypes), `lms.lms.trainee_test_utils.make_user`/`make_trainee` (existing, safe to reuse outside tests since they're plain functions, not test-only).

- [ ] **Step 1: Write the seed script**

Create `backend/lms/patches/ops_checklist_seed_demo_data.py`:

```python
"""One-off local seed for manually dogfooding the Ops Checklist feature.
Run with: bench --site frappe.local execute lms.patches.ops_checklist_seed_demo_data.run
Not registered in patches.txt — this is demo data, not a schema migration."""

import frappe

from lms.lms.trainee_test_utils import make_trainee, make_user


def run():
	cohort = frappe.get_doc(
		{
			"doctype": "Sales Trainee Cohort",
			"cohort_name": "Ops-Checklist-Demo",
			"start_date": "2026-09-01",
			"expected_completion_date": "2026-09-25",
		}
	).insert(ignore_permissions=True)

	manager = make_user("demo-manager", "Sales Trainee Manager")
	make_user("demo-team", "Sales Training Team")
	make_user("demo-finance", "Sales Training Finance")
	make_user("demo-leadership", "Sales Training Leadership")

	# In Training past the cohort's expected completion date, and with no attendance
	# marked today — exercises both live-checklist item types at once.
	make_trainee(
		"Demo Overdue Trainee", assigned_sales_manager=manager, cohort=cohort.name, training_status="In Training"
	)

	frappe.get_doc(
		{
			"doctype": "Weekly Payroll Cycle",
			"week_start": "2026-09-22",
			"week_end": "2026-09-28",
			"cohort": cohort.name,
			"status": "Awaiting Invoice",
		}
	).insert(ignore_permissions=True)

	frappe.db.commit()
	print("Seeded: cohort=%s, manager=demo-manager@..., 1 overdue trainee, 1 open payroll cycle" % cohort.name)
```

- [ ] **Step 2: Run the seed script against local dev**

Run: `~/.frappe-bench-cli/bin/bench --site frappe.local execute lms.patches.ops_checklist_seed_demo_data.run`
Expected: prints the "Seeded: ..." confirmation line, no traceback.

- [ ] **Step 3: Manually walk the checklist as each of the 4 seeded roles**

In the browser (real Chrome via Claude-in-Chrome, or the built-in browser pane — not just curl/API calls, per this project's established rehearsal practice), log in as each of `demo-manager`, `demo-team`, `demo-finance`, `demo-leadership` and confirm:
- `demo-manager` and `demo-team` both see the overdue-attendance item for `Ops-Checklist-Demo`.
- `demo-finance` sees the open payroll-cycle item.
- `demo-leadership` sees only the read-only summary, no action items.
- Each role's tour banner copy matches their role (per `tourCopy` in Task 3).

- [ ] **Step 4: Flag for real acceptance**

This task's deliverable is the seed script plus a confirmation that the internal walkthrough passed — record that confirmation as a commit message note. The actual acceptance gate (Madan/Atul using this against one real, current cohort) happens after this plan ships and is not a step this plan can perform — surface it to Vijay as the next action once Task 5 is committed.

- [ ] **Step 5: Commit**

```bash
git add backend/lms/patches/ops_checklist_seed_demo_data.py
git commit -m "test(sales): add Ops Checklist demo-data seed script for dogfooding"
```
