# Consumer Sales Training & Third-Party Payroll Tracker — Design Spec

Source requirement: [Consumer Sales Training & Third-Party Payroll Tracker](https://infinitylearn.atlassian.net/wiki/spaces/~7120200816e36e73d440c6982689ec4e171458/pages/2901409801/) (MoM, Confluence, last modified 2026-09-22).

Status: DRAFT — pending Vijay's review of this spec. The source doc itself has 10 open items pending validation with Madan/Sales/Finance (§9); this spec builds V1 on the doc's stated assumptions and does not block on those business-rule confirmations (see §8).

## 1. Objective

Build a portal, inside the existing `lms` Frappe app (this repo), to track Consumer Sales (Academic Counsellor) trainees from date of joining through training completion or exit, while they remain on third-party vendor payroll for month 1. Goal: stop trainees entering InfinityLearn HRMS before the active cohort is confirmed, get attendance/payroll inputs closed early enough for on-time vendor invoicing and 1st-of-month salary runs, and give the business one place (instead of Excel + manual coordination) to see trainee status, attendance, and payroll-cycle state.

Trainee login, self-service, and biometric/punch/geo attendance are explicitly out of scope (§7). Staff mark data on trainees' behalf throughout.

## 2. Architecture decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Where it lives | New DocTypes inside the existing `lms` Frappe app, this repo | Reuses Frappe infra, permission engine, Vue shell, one deploy pipeline. No new service. |
| Trainee identity | `Sales Trainee` is a **standalone DocType**, not `Link→User` | First non-User-linked identity record in this app. Matches "trainee login out of scope" and "tracking must not depend on an employee code being available from Day 1" (source doc §3). |
| Staff identity | Real Frappe Users + Roles, reusing the existing reporting-line/permission-scoping pattern (`access.py`, `permission_query_conditions`) | Explicit steer: reuse what's already built for Training Team/Sales Manager/Finance/Leadership access. |
| Payroll calculation | **Capture only** — inputs (salary, days, dates) and the vendor's returned invoice amount, side by side, for Finance to reconcile. No pro-rata formula implemented. | Source doc's own open item #6 says the formula is still unknown; vendor calculates and invoices it. Building a formula now would be building on a guess. |
| Roles | 4 new Frappe Roles: Sales Training Team, Sales Trainee Manager, Sales Training Finance, Sales Training Leadership. Super Admin = existing `System Manager`. | None of these exist today; only `System Manager`, `LMS Manager`, `Course Creator`, `Batch Evaluator`, `LMS Student` do. |
| CRT-week attendance source | Dual: pull from the existing Zoom-based live-class attendance sync (`lms_live_class.py::get_attendance`/`create_attendance`) when available, else manually marked by Training Team. OJT weeks are always manual. | Explicit steer: reuse existing Zoom sync where it exists; this portal is the single ledger either way. |
| Bulk onboarding pattern | Model on `ojt_certification.py`'s CSV/Sheet upsert (dedup by email, dry-run validation, partial-failure-safe upsert-by-row-key), not the CRT curriculum importer | Closer match: per-person rows with dedup, not a curriculum schedule. |

## 3. Data model (new DocTypes)

### `Sales Trainee`
Not linked to a Frappe User. Created via bulk onboarding as soon as Sales confirms a hire.

| Field | Type | Notes |
|---|---|---|
| trainee_name | Data | |
| personal_email | Data | Onboarding dedup key |
| phone | Data | |
| location | Data | |
| date_of_joining | Date | Attendance/tracking starts here, independent of employee code |
| salary | Currency | |
| cohort | Link → `Sales Trainee Cohort` | |
| training_status | Select | In Training / Resigned / Absconded / Exited-Churned / Training Cleared / Training Not Cleared |
| employee_dummy_vendor_code | Data | Blank until Day 3; set once active cohort is confirmed |
| ta_spoc | Link → User | Recruiter who sourced the hire |
| assigned_trainer | Link → User | Owns attendance/status through Day 21 |
| assigned_sales_manager | Link → User | Owns/regularizes attendance from Day 22; drives permission scoping (reporting-tree recursion via `access.py`) |
| exit_status | Select | mirrors training_status exit values |
| exit_date | Date | |
| exit_reason | Small Text | |

### `Sales Trainee Cohort`
| Field | Type | Notes |
|---|---|---|
| cohort_name | Data | |
| location | Data | |
| start_date | Date | |
| trainer | Link → User | |
| expected_completion_date | Date | |

Total/active/exit/outcome counts are computed on read (report query), not stored — avoids staleness.

### `Sales Trainee Attendance`
| Field | Type | Notes |
|---|---|---|
| trainee | Link → Sales Trainee | |
| attendance_date | Date | |
| status | Select | Present / Absent / Leave / Holiday |
| source | Select | Zoom Sync / Manual | Set automatically; CRT-week rows may be Zoom-populated, OJT-week rows always Manual |
| marked_by | Link → User | |

Corrections go through `Sales Trainee Audit Log`, not silent field overwrite.

### `Sales Trainee Audit Log`
Generalizes the existing `LMS Identity Change` shape for this module.

| Field | Type | Notes |
|---|---|---|
| trainee | Link → Sales Trainee | |
| field_changed | Data | e.g. "attendance:2026-10-03", "training_status" |
| old_value | Data | |
| new_value | Data | |
| changed_by | Link → User | |
| changed_on | Datetime | |
| reason | Small Text | Required for attendance corrections and status changes |

### `Weekly Payroll Cycle`
| Field | Type | Notes |
|---|---|---|
| week_start / week_end | Date | |
| cohort | Link → Sales Trainee Cohort | Optional — a cycle can span cohorts |
| status | Select | Preparing / Ready to Share / Shared with Vendor / Awaiting Invoice / Finance Validation / Closed |
| shared_on | Datetime | |
| vendor_invoice_amount | Currency | What the vendor returns — captured, not computed |
| finance_validated_by / finance_validated_on | Link → User / Datetime | |
| exceptions_notes | Small Text | |

### `Weekly Payroll Input` (child of `Weekly Payroll Cycle`)
| Field | Type | Notes |
|---|---|---|
| trainee | Link → Sales Trainee | |
| salary | Currency | Snapshot at cycle time |
| working_days | Int | |
| payable_days | Int | Derived from `Sales Trainee Attendance` |
| joining_or_exit_adjustment_note | Small Text | |

No calculated pro-rata field — Finance reconciles `payable_days`/`salary` against `vendor_invoice_amount` manually (§2).

## 4. Roles & permission scoping

New Frappe Roles: `Sales Training Team`, `Sales Trainee Manager`, `Sales Training Finance`, `Sales Training Leadership`. `Super Admin` tier maps to existing `System Manager` (full access, matches how Admin already works elsewhere in this app).

Visibility reuses the existing pattern:
- `permission_query_conditions` registered for `Sales Trainee`/`Sales Trainee Attendance`/`Weekly Payroll Cycle`, same shape as the existing hooks for `LMS Course`/`LMS Batch` (`hooks.py:124-131`).
- Scoping logic lives alongside `access.py`'s reporting-tree recursion (`managers_above`): a `Sales Trainee Manager` sees trainees where they are `assigned_sales_manager`, or are above that manager in the existing `LMS Reporting Line` chain.
- `Sales Training Finance` sees payroll-cycle data org-wide (read + validate), not trainee personal fields beyond what's needed for reconciliation.
- `Sales Training Leadership` is read-only on dashboards/reports.

Day-22 handover (Training Team → Sales Manager owning attendance) is a `date_of_joining`-based check in the `Sales Trainee Attendance` controller's `has_permission`, not a manual reassignment step.

## 5. Bulk onboarding

New Vue screen modeled on `SalesImport.vue`, backed by a CSV/Excel parser modeled on `ojt_certification.py`'s sync (`sync_ojt_certification_metrics`/`replace_ojt_certification_rows`):
- Dedup key: `personal_email` (+ cohort, if the same person is re-uploaded into a different cohort intentionally).
- Dry-run validation pass: flags missing mandatory fields and duplicate rows before commit, same UX as the existing importer.
- Upsert-by-row-key, update-in-place — avoids the delete-then-reinsert gap the existing importer explicitly avoids.

## 6. Attendance

- `Sales Trainee Attendance` is the single ledger for the full 21-day window (CRT week 1 + OJT weeks 2–3).
- CRT-week rows: where a Zoom-synced live class exists for that trainee/date, auto-populate from the existing `lms_live_class.py::get_attendance`/`create_attendance` sync; otherwise Training Team marks manually.
- OJT-week rows: always manually marked by Training Team (Day 1–21), handed to Sales Manager from Day 22.
- No self-marking, punch-in, biometric, or geo-location — matches doc's explicit exclusion (§7).
- All corrections (any source) go through `Sales Trainee Audit Log` with a required reason.

## 7. Out of scope (V1)

Trainee login/signup/self-service portal; punch-in/biometric/geo-location attendance; direct salary/payroll disbursement; replacing the third-party vendor payroll system; full InfinityLearn HRMS functionality; pro-rata calculation logic (§2); the Month-2 conversion of a cleared trainee into a real `lms_member`/User account (not listed in the source doc's V1 scope — remains a manual HRMS step outside this portal).

## 8. Open items not blocking this build

The source doc lists 10 items still pending validation with Madan/Sales (statuses sufficiency, exact exit-detail requirements, employee/dummy code ownership, weekly cutoff timing, pro-rata formula, correction/exception handling, report templates, cohort-management necessity). This spec builds V1 on the doc's stated current assumptions for all of them and does not wait on that validation — consistent with the doc's own "Next Steps," which puts prototype-build before Sales/Finance validation of the prototype. Revisit these fields/flows once that validation lands; none of them change the architecture in §2.

## 9. Dashboard & reports

New Vue section (sibling to existing Reports/Analytics), filters: month, location, cohort/batch. Metrics and exports as listed verbatim in the source doc §8–9 (trainee counts by status/location/cohort, payroll-eligible trainees, attendance/payroll status, weekly attendance/payroll report, vendor payroll input, active/exit/training-outcome reports, finance reconciliation report). Exports via the existing `openpyxl` dependency, Excel/CSV.
