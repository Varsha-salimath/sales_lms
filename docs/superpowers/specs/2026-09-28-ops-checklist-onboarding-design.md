# Ops Checklist (Staff Onboarding/Compliance Guide) — Design Spec

Source: brainstorm session 2026-09-28, request relayed by Vijay from Madan (Sales Manager HR). Full narrative in vault: `~/KnowledgeOS/04_Projects/infinitylearn/saleslms/sessions.md` (2026-09-28 "Brainstorm: new 'guided onboarding' feature request").

Status: DRAFT — pending Vijay's review of this spec.

## 1. Objective

Give staff running the Consumer Sales Training pipeline (Sales Training Team, Sales Trainee Manager, Sales Training Finance, Sales Training Leadership) a guided, role-scoped view of what SOP step is due next, using data that already exists in the app today. Two parts:

- A **static first-login tour**, per role, explaining the SOP flow once.
- A **persistent live checklist**, always visible via a sidebar badge, surfacing real overdue items (unmarked attendance, un-certified trainees, an approaching payroll-export deadline) pulled from existing data — not a new tracking system.

**Explicitly not in scope** (walked back from an earlier, larger brainstorm draft that over-reached): no new pre-join/offer-letter/DOJ/vendor-billing-reconciliation tracking. This feature is a guidance layer over functionality the app already has. No new role. No trainee-facing surface — trainee self-service login remains out of scope per the 2026-09-24 decision.

## 2. Architecture decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Name | "Ops Checklist" (working title, Vijay may rename) | Avoids collision with the existing learner-facing `SalesOnboardingHome.vue`, which already owns the term "onboarding" in this app and is the entire post-login student dashboard (`frontend/src/pages/Dashboard/Dashboard.vue`). |
| Audience | Internal staff only — the 4 existing sales roles | Resolves the literal "anyone opening the app" ask against the standing "no trainee self-service" decision; confirmed explicitly with Vijay. |
| Roles → people (informational, not enforced in code) | Sales Training Team = Madan; Sales Training Leadership = Atul | Per Vijay 2026-09-28. Not hardcoded — role-based like everything else in this app; if the actual Frappe role assignment differs, only the role-to-person mapping in this doc is wrong, not the design. |
| Visual language | `genius-*` (staff/admin, utilitarian) not `il-*` (learner, branded) | Matches every other staff screen (`TraineeList.vue`, `TraineeAttendanceHistory.vue`, `WeeklyPayrollCycle.vue`). |
| New data model | None for checklist content — read-only aggregation over existing DocTypes/APIs | Explicit scope correction 2026-09-28: guide layer only, no new SOP-tracking infrastructure. |
| New data model, minimal | One new doctype for tour-seen state (see §3) | Nothing existing captures "has this user dismissed this tour." |
| Placement | Sidebar badge (always visible, in `AppSidebar.vue`) + dedicated `/ops-checklist` page | Directly answers "guided wherever they open the app" without forcing a single landing page. |

## 3. Data model

### `Ops Checklist Tour State` (new, minimal)

| Field | Type | Notes |
|---|---|---|
| user | Link → User | |
| role_context | Data | The role the tour was shown for (a user could hold more than one of the 4 roles) |
| skipped_on | Datetime | Null until skipped |

One row per (user, role_context). Presence of a non-null `skipped_on` row = tour is dismissed for that user+role; absence = show the tour. No other new storage — the live checklist is computed on read every time, never persisted, so it can never go stale.

### Existing data reused (no changes)

- `trainee_cohort_stats.list_missing_attendance` — cohorts/weeks with unmarked attendance.
- `trainee_dashboard.get_dashboard_summary` — headcount/status summary (Leadership's read-only view).
- `Weekly Payroll Cycle.status` + its date fields — open-cycle and days-to-25th countdown.
- `Sales Trainee.training_status` — CRT-complete-but-not-certified detection (cross-reference against `LMS Certificate` issuance).
- `trainee_scope.py` role/reporting-tree logic — reused unchanged to scope what each Sales Trainee Manager sees.

## 4. Backend

One new whitelisted method per role's checklist content (or one method taking role as an implicit parameter from `frappe.session.user`'s roles — implementation detail for the plan, not the spec), each composed from existing read APIs, no new writes except tour-skip:

- **Sales Training Team**: cohorts with any unmarked CRT or OJT attendance this week; trainees CRT-complete but not yet certified; days remaining until the 25th payroll-export deadline.
- **Sales Trainee Manager**: same attendance check, scoped to their own reporting tree only (reuse `trainee_scope.py`).
- **Sales Training Finance**: payroll cycles not yet closed; reconciliation export not yet run for the current cycle.
- **Sales Training Leadership**: no action items — read-only summary numbers only (reuses `get_dashboard_summary`). Tour still applies; live checklist section is display-only for this role.

Two more whitelisted methods: `get_ops_checklist_tour_state()` / `skip_ops_checklist_tour()`.

**Error handling**: each checklist section is fetched/rendered independently; if one sub-query throws, that card shows "Couldn't load this section" and the rest of the page still renders — matches the existing dashboard's defensive pattern (no single point of failure taking down the whole page).

## 5. Frontend

- `frontend/src/pages/Sales/OpsChecklist.vue` (new) — `genius-*` styled. Layout: step-list shape borrowed structurally from `SalesOnboardingHome.vue` (progress indicator + list of items with status), re-skinned for staff. Two zones:
  - **Tour banner** (top, only if not yet skipped for this user+role): short explanatory copy per role, a **"Skip" button** (permanent — writes `skip_ops_checklist_tour()`, never shown again unless replayed), and a "Replay tour" link surfaced elsewhere (e.g. a help/`?` menu) for anyone who skipped and wants it back.
  - **Live checklist** (always visible, not skippable/dismissible by design — it's a compliance nudge, it clears itself only when the underlying task is actually done): one card per pending item, plain-language copy, a CTA linking straight to the existing screen where the action happens (e.g. straight into `TraineeAttendanceHistory.vue` filtered to the overdue cohort/week).
- `frontend/src/components/Sidebar/AppSidebar.vue` (existing, modified) — small pending-count badge next to the nav entry linking to `/ops-checklist`. Count = live checklist item count only (tour state doesn't affect the badge).
- `frontend/src/router.js` — new route `/ops-checklist`, gated the same way existing `staffOnlyRoutes`/`salesTrainingRoutes` are (lines ~536-591), no new role added to the gate.

## 6. Copy ("custom messages")

Plain-language, action-first, drafted by Claude per role/step (e.g. *"Week 3 attendance not marked for 2 cohorts — mark it before Friday"*, not *"Attendance status: incomplete"*). Vijay/Madan review and edit before ship — this spec does not lock exact copy, only the pattern (what's wrong → what to do → by when, where known).

## 7. Testing / rollout

1. Seed realistic pending-state data (overdue attendance across CRT/OJT weeks, a payroll cycle nearing the 25th, a CRT-complete-uncertified trainee) in a local/dev environment.
2. Internal walkthrough (Vijay/Claude) across all 4 roles against seeded data — same method as the 2026-09-28 live-demo rehearsal on this branch (real browser, not just unit tests) — before handing to anyone else.
3. Real acceptance: Madan and Atul use it against real, current data for at least one live cycle before considering this done.
4. Automated coverage: unit/integration tests for each role's aggregator method (mirroring the existing `test_trainee_role_scoping.py` pattern for reporting-tree scoping), plus a test for tour skip/replay state transitions.

## 8. Open items / explicit non-goals

- Exact badge/count refresh cadence (poll on page load vs. periodic refresh) — implementation detail for the plan, not locked here.
- Exact tour copy per role — drafted during implementation, reviewed before ship (§6).
- Confirmed earlier and explicitly out of scope: any new pre-join/offer-letter/DOJ/vendor-billing-reconciliation tracking. If that is still wanted, it is a separate, later spec — not part of this one.
