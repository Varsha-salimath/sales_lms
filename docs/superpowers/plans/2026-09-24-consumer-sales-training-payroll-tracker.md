# Consumer Sales Training & Third-Party Payroll Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a trainee-tracking module to the existing `lms` Frappe app that follows Consumer Sales (Academic Counsellor) trainees from joining through training completion/exit — onboarding, cohort management, attendance, lifecycle status, capture-only payroll inputs, and reporting — while they remain on third-party vendor payroll for month 1.

**Architecture:** New DocTypes inside the existing `backend/lms/` Frappe app (module `LMS`), no new service. `Sales Trainee` is a standalone identity (not `Link→User`) since trainees never log in in V1. Staff access reuses the existing `access.py` reporting-tree/permission pattern via 4 new Frappe Roles. Attendance is a single ledger populated either by the existing Zoom live-class sync or by manual staff entry. Payroll is capture-only — no pro-rata formula.

**Tech Stack:** Frappe (Python ≥3.10), MariaDB, Vue 3 + `frappe-ui` (frontend), `openpyxl` for exports. Test runner: Frappe's own `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-09-24-consumer-sales-training-payroll-tracker-design.md`

## Global Constraints

- Module name on every new DocType JSON: `"module": "LMS"` (this app has one module; doctypes don't get their own).
- `Sales Trainee` must never become `Link→User` — trainee login is out of scope for V1 (spec §7).
- No punch-in / biometric / geo-location attendance in V1 (spec §6, §7).
- No pro-rata calculation logic anywhere — capture the vendor's returned `vendor_invoice_amount` only (spec §2, §3).
- New Roles, exact names: `Sales Training Team`, `Sales Trainee Manager`, `Sales Training Finance`, `Sales Training Leadership`. Super Admin tier = existing `System Manager` role (spec §4).
- Python style: tabs, double quotes, ruff/isort per `backend/pyproject.toml`. `frappe = ">=14.0.0,<=17.0.0-dev"`.
- Test command for a single module: `bench --site frappe.local run-tests --app lms --module <dotted.module.path>`. Full suite (CI): `bench --site frappe.local run-tests --app lms --coverage`.
- CSV/Excel exports use the existing `openpyxl` dependency — don't add a new library.
- Bulk-import dedup/upsert follows the existing `ojt_certification.py` `make_row_key` + upsert-by-key pattern, not the CRT curriculum importer.

## Review Focus

- Marking attendance for a trainee on a date that already has a row must update it, not create a duplicate (double-counts payable days downstream) — tested in Task 4.
- Bulk-uploading a trainee whose email was already onboarded (re-upload, or moved cohort) must update the existing `Sales Trainee` in place, not create a second record — tested in Task 7.
- Correcting attendance after its `Weekly Payroll Cycle` has moved to "Shared with Vendor" or "Closed" must still be allowed and audit-logged, not silently blocked — the doc calls this out as an explicit open question, and blocking it would trap Training Team with no recourse — tested in Task 4.
- A trainee whose `exit_date` falls inside an open payroll week must stop counting payable days at `exit_date`, not run through the full week — tested in Task 9.
- A brand-new trainee with no `assigned_sales_manager` set yet (Day 1–3, before cohort confirmation) must still be visible to their `assigned_trainer` and to Super Admin/Finance/Leadership — an empty scoping condition must not silently hide them from everyone — tested in Task 6.

---

## File Structure

```
backend/lms/lms/doctype/
  sales_trainee_cohort/
    sales_trainee_cohort.json
    sales_trainee_cohort.py
    test_sales_trainee_cohort.py
    __init__.py
  sales_trainee/
    sales_trainee.json
    sales_trainee.py
    test_sales_trainee.py
    __init__.py
  sales_trainee_audit_log/
    sales_trainee_audit_log.json
    sales_trainee_audit_log.py
    test_sales_trainee_audit_log.py
    __init__.py
  sales_trainee_attendance/
    sales_trainee_attendance.json
    sales_trainee_attendance.py
    test_sales_trainee_attendance.py
    __init__.py
  weekly_payroll_cycle/
    weekly_payroll_cycle.json
    weekly_payroll_cycle.py
    test_weekly_payroll_cycle.py
    __init__.py
  weekly_payroll_input/
    weekly_payroll_input.json
    weekly_payroll_input.py
    __init__.py
backend/lms/lms/
  trainee_scope.py              # permission_query_conditions + has_permission for the 3 scoped doctypes
  sales_trainee_import.py       # bulk onboarding CSV/row upsert
  trainee_attendance_sync.py    # Zoom live-class -> Sales Trainee Attendance bridge
  trainee_payroll.py            # payable-days computation, weekly input prep
  trainee_reports.py            # CSV/Excel export endpoints
  test_trainee_scope.py
  test_sales_trainee_import.py
  test_trainee_attendance_sync.py
  test_trainee_payroll.py
backend/lms/hooks.py             # MODIFY: permission_query_conditions, has_permission, doc_events
frontend/src/pages/Sales/
  TraineeImport.vue
  TraineeCohortList.vue
  TraineeList.vue
  TraineeAttendance.vue
  WeeklyPayrollCycle.vue
  TraineeDashboard.vue
frontend/src/router.js           # MODIFY: add routes, extend staffOnlyRoutes
frontend/src/utils/index.js      # MODIFY: add nav entries
```

---

### Task 1: Sales Trainee Cohort DocType

**Files:**
- Create: `backend/lms/lms/doctype/sales_trainee_cohort/__init__.py`
- Create: `backend/lms/lms/doctype/sales_trainee_cohort/sales_trainee_cohort.json`
- Create: `backend/lms/lms/doctype/sales_trainee_cohort/sales_trainee_cohort.py`
- Test: `backend/lms/lms/doctype/sales_trainee_cohort/test_sales_trainee_cohort.py`

**Interfaces:**
- Produces: DocType `Sales Trainee Cohort` with fields `cohort_name` (primary key via autoname), `location`, `start_date`, `trainer` (Link→User), `expected_completion_date`. Later tasks link to it via `Link→Sales Trainee Cohort`.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/sales_trainee_cohort/test_sales_trainee_cohort.py
import frappe
from frappe.tests import UnitTestCase


class TestSalesTraineeCohort(UnitTestCase):
	def test_create_cohort(self):
		cohort = frappe.get_doc(
			{
				"doctype": "Sales Trainee Cohort",
				"cohort_name": "Hyderabad-Oct-W1",
				"location": "Hyderabad",
				"start_date": "2026-10-06",
			}
		)
		cohort.insert(ignore_permissions=True)
		self.assertEqual(cohort.name, "Hyderabad-Oct-W1")
		self.assertTrue(frappe.db.exists("Sales Trainee Cohort", "Hyderabad-Oct-W1"))

	def test_duplicate_cohort_name_rejected(self):
		frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": "Blr-Oct-W1", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{"doctype": "Sales Trainee Cohort", "cohort_name": "Blr-Oct-W1", "start_date": "2026-10-13"}
			).insert(ignore_permissions=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_cohort.test_sales_trainee_cohort -v`
Expected: FAIL — `Sales Trainee Cohort` DocType does not exist yet.

- [ ] **Step 3: Create the DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "cohort_name", "location", "column_break_1", "start_date", "expected_completion_date", "trainer"
 ],
 "fields": [
  {"fieldname": "cohort_name", "fieldtype": "Data", "label": "Cohort Name", "reqd": 1, "unique": 1, "in_list_view": 1},
  {"fieldname": "location", "fieldtype": "Data", "label": "Location", "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "column_break_1", "fieldtype": "Column Break"},
  {"fieldname": "start_date", "fieldtype": "Date", "label": "Start Date", "reqd": 1, "in_list_view": 1},
  {"fieldname": "expected_completion_date", "fieldtype": "Date", "label": "Expected Completion Date"},
  {"fieldname": "trainer", "fieldtype": "Link", "label": "Trainer", "options": "User", "in_standard_filter": 1}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Sales Trainee Cohort",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1, "email": 1, "share": 1},
  {"role": "Sales Training Team", "read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1},
  {"role": "Sales Trainee Manager", "read": 1, "report": 1},
  {"role": "Sales Training Finance", "read": 1, "report": 1, "export": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": [],
 "title_field": "cohort_name",
 "autoname": "field:cohort_name",
 "naming_rule": "By fieldname",
 "track_changes": 1
}
```

- [ ] **Step 4: Create the controller**

```python
# backend/lms/lms/doctype/sales_trainee_cohort/sales_trainee_cohort.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SalesTraineeCohort(Document):
	pass
```

```python
# backend/lms/lms/doctype/sales_trainee_cohort/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_cohort.test_sales_trainee_cohort -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee_cohort/
git commit -m "feat: add Sales Trainee Cohort doctype"
```

---

### Task 2: Sales Trainee DocType

**Files:**
- Create: `backend/lms/lms/doctype/sales_trainee/__init__.py`
- Create: `backend/lms/lms/doctype/sales_trainee/sales_trainee.json`
- Create: `backend/lms/lms/doctype/sales_trainee/sales_trainee.py`
- Test: `backend/lms/lms/doctype/sales_trainee/test_sales_trainee.py`

**Interfaces:**
- Consumes: `Sales Trainee Cohort` (Task 1).
- Produces: DocType `Sales Trainee` — the standalone (no `Link→User`) trainee identity. Fields: `trainee_name`, `personal_email` (unique, dedup key for Tasks 6, 7, 8, 9), `phone`, `location`, `date_of_joining`, `salary`, `cohort` (Link), `training_status`, `employee_dummy_vendor_code`, `ta_spoc`/`assigned_trainer`/`assigned_sales_manager` (Link→User — these three are what later permission scoping keys off), `exit_status`, `exit_date`, `exit_reason`.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/sales_trainee/test_sales_trainee.py
import frappe
from frappe.tests import UnitTestCase


class TestSalesTrainee(UnitTestCase):
	def test_create_trainee_defaults_to_in_training(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Asha Rao",
				"personal_email": "asha.rao.candidate@example.com",
				"phone": "9876543210",
				"date_of_joining": "2026-10-06",
			}
		)
		trainee.insert(ignore_permissions=True)
		self.assertEqual(trainee.training_status, "In Training")
		self.assertEqual(trainee.employee_dummy_vendor_code, None)

	def test_duplicate_email_rejected(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "First",
				"personal_email": "dup@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": "Sales Trainee",
					"trainee_name": "Second",
					"personal_email": "dup@example.com",
					"date_of_joining": "2026-10-06",
				}
			).insert(ignore_permissions=True)

	def test_no_user_link_field_exists(self):
		meta = frappe.get_meta("Sales Trainee")
		for field in meta.fields:
			if field.fieldtype == "Link" and field.options == "User":
				continue  # ta_spoc / assigned_trainer / assigned_sales_manager are expected staff links
			self.assertNotEqual(
				(field.fieldtype, field.options), ("Link", "User"),
				"Sales Trainee must stay standalone for the trainee identity itself",
			)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee.test_sales_trainee -v`
Expected: FAIL — DocType does not exist.

- [ ] **Step 3: Create the DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "trainee_name", "personal_email", "phone", "column_break_1", "location", "date_of_joining", "salary",
  "section_break_training", "cohort", "training_status", "employee_dummy_vendor_code",
  "section_break_owners", "ta_spoc", "assigned_trainer", "assigned_sales_manager",
  "section_break_exit", "exit_status", "exit_date", "exit_reason"
 ],
 "fields": [
  {"fieldname": "trainee_name", "fieldtype": "Data", "label": "Trainee Name", "reqd": 1, "in_list_view": 1},
  {"fieldname": "personal_email", "fieldtype": "Data", "label": "Personal Email", "reqd": 1, "unique": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
  {"fieldname": "column_break_1", "fieldtype": "Column Break"},
  {"fieldname": "location", "fieldtype": "Data", "label": "Location", "in_standard_filter": 1},
  {"fieldname": "date_of_joining", "fieldtype": "Date", "label": "Date of Joining", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "salary", "fieldtype": "Currency", "label": "Salary"},
  {"fieldname": "section_break_training", "fieldtype": "Section Break", "label": "Training"},
  {"fieldname": "cohort", "fieldtype": "Link", "label": "Cohort", "options": "Sales Trainee Cohort", "in_standard_filter": 1},
  {"fieldname": "training_status", "fieldtype": "Select", "label": "Training Status", "reqd": 1, "default": "In Training", "in_list_view": 1, "in_standard_filter": 1,
   "options": "In Training\nResigned\nAbsconded\nExited/Churned\nTraining Cleared\nTraining Not Cleared"},
  {"fieldname": "employee_dummy_vendor_code", "fieldtype": "Data", "label": "Employee/Dummy/Vendor Code"},
  {"fieldname": "section_break_owners", "fieldtype": "Section Break", "label": "Ownership"},
  {"fieldname": "ta_spoc", "fieldtype": "Link", "label": "TA SPOC", "options": "User"},
  {"fieldname": "assigned_trainer", "fieldtype": "Link", "label": "Assigned Trainer", "options": "User", "in_standard_filter": 1},
  {"fieldname": "assigned_sales_manager", "fieldtype": "Link", "label": "Assigned Sales Manager", "options": "User", "in_standard_filter": 1},
  {"fieldname": "section_break_exit", "fieldtype": "Section Break", "label": "Exit", "depends_on": "eval:['Resigned','Absconded','Exited/Churned'].includes(doc.training_status)"},
  {"fieldname": "exit_status", "fieldtype": "Select", "label": "Exit Status", "options": "\nResigned\nAbsconded\nExited/Churned"},
  {"fieldname": "exit_date", "fieldtype": "Date", "label": "Exit Date"},
  {"fieldname": "exit_reason", "fieldtype": "Small Text", "label": "Exit Reason"}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Sales Trainee",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1, "email": 1, "share": 1},
  {"role": "Sales Training Team", "read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1},
  {"role": "Sales Trainee Manager", "read": 1, "write": 1, "report": 1, "export": 1},
  {"role": "Sales Training Finance", "read": 1, "report": 1, "export": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": [],
 "title_field": "trainee_name",
 "autoname": "ST-.YYYY.-.#####",
 "naming_rule": "Expression (old style)",
 "track_changes": 1
}
```

- [ ] **Step 4: Create the controller**

```python
# backend/lms/lms/doctype/sales_trainee/sales_trainee.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SalesTrainee(Document):
	pass
```

```python
# backend/lms/lms/doctype/sales_trainee/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee.test_sales_trainee -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee/
git commit -m "feat: add standalone Sales Trainee doctype (no login, no User link)"
```

---

### Task 3: Sales Trainee Audit Log DocType

**Files:**
- Create: `backend/lms/lms/doctype/sales_trainee_audit_log/__init__.py`
- Create: `backend/lms/lms/doctype/sales_trainee_audit_log/sales_trainee_audit_log.json`
- Create: `backend/lms/lms/doctype/sales_trainee_audit_log/sales_trainee_audit_log.py`
- Test: `backend/lms/lms/doctype/sales_trainee_audit_log/test_sales_trainee_audit_log.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2).
- Produces: `write_audit_log(trainee, field_changed, old_value, new_value, reason, changed_by=None)` helper function in `sales_trainee_audit_log.py`, used by Tasks 4 and 5's correction flows. Insert-only — a second `.save()` on an existing row raises.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/sales_trainee_audit_log/test_sales_trainee_audit_log.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log


class TestSalesTraineeAuditLog(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Audit Target",
				"personal_email": f"audit-target-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_write_audit_log_records_reason(self):
		log = write_audit_log(
			trainee=self.trainee.name,
			field_changed="training_status",
			old_value="In Training",
			new_value="Training Cleared",
			reason="Cleared final viva",
		)
		self.assertEqual(log.reason, "Cleared final viva")
		self.assertEqual(log.trainee, self.trainee.name)

	def test_reason_is_mandatory(self):
		with self.assertRaises(frappe.MandatoryError):
			write_audit_log(
				trainee=self.trainee.name,
				field_changed="training_status",
				old_value="In Training",
				new_value="Resigned",
				reason="",
			)

	def test_audit_log_cannot_be_edited_after_creation(self):
		log = write_audit_log(
			trainee=self.trainee.name,
			field_changed="training_status",
			old_value="In Training",
			new_value="Resigned",
			reason="Resigned on Day 5",
		)
		log.reason = "Changed my mind"
		with self.assertRaises(frappe.ValidationError):
			log.save(ignore_permissions=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_audit_log.test_sales_trainee_audit_log -v`
Expected: FAIL — DocType/module does not exist.

- [ ] **Step 3: Create the DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["trainee", "field_changed", "column_break_1", "old_value", "new_value", "changed_by", "changed_on", "reason"],
 "fields": [
  {"fieldname": "trainee", "fieldtype": "Link", "label": "Trainee", "options": "Sales Trainee", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "field_changed", "fieldtype": "Data", "label": "Field Changed", "reqd": 1, "in_list_view": 1},
  {"fieldname": "column_break_1", "fieldtype": "Column Break"},
  {"fieldname": "old_value", "fieldtype": "Data", "label": "Old Value"},
  {"fieldname": "new_value", "fieldtype": "Data", "label": "New Value"},
  {"fieldname": "changed_by", "fieldtype": "Link", "label": "Changed By", "options": "User", "reqd": 1, "read_only": 1},
  {"fieldname": "changed_on", "fieldtype": "Datetime", "label": "Changed On", "reqd": 1, "read_only": 1, "default": "now"},
  {"fieldname": "reason", "fieldtype": "Small Text", "label": "Reason", "reqd": 1, "in_list_view": 1}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Sales Trainee Audit Log",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 0, "create": 1, "delete": 0, "report": 1, "export": 1, "print": 1},
  {"role": "Sales Training Team", "read": 1, "create": 1, "report": 1},
  {"role": "Sales Trainee Manager", "read": 1, "create": 1, "report": 1},
  {"role": "Sales Training Finance", "read": 1, "report": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "changed_on",
 "sort_order": "DESC",
 "states": [],
 "title_field": "field_changed",
 "autoname": "TAL-.YYYY.-.#####",
 "naming_rule": "Expression (old style)",
 "track_changes": 0
}
```

- [ ] **Step 4: Create the controller with the insert-only guard and the helper**

```python
# backend/lms/lms/doctype/sales_trainee_audit_log/sales_trainee_audit_log.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SalesTraineeAuditLog(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Audit log entries cannot be edited after creation."))
		if not (self.reason or "").strip():
			frappe.throw(_("A reason is required for every audit log entry."), frappe.MandatoryError)


def write_audit_log(trainee, field_changed, old_value, new_value, reason, changed_by=None):
	"""Create one immutable audit entry. Raises frappe.MandatoryError if reason is blank."""
	log = frappe.get_doc(
		{
			"doctype": "Sales Trainee Audit Log",
			"trainee": trainee,
			"field_changed": field_changed,
			"old_value": old_value,
			"new_value": new_value,
			"changed_by": changed_by or frappe.session.user,
			"reason": reason,
		}
	)
	log.insert(ignore_permissions=True)
	return log
```

```python
# backend/lms/lms/doctype/sales_trainee_audit_log/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_audit_log.test_sales_trainee_audit_log -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee_audit_log/
git commit -m "feat: add insert-only Sales Trainee Audit Log doctype"
```

---

### Task 4: Sales Trainee Attendance DocType + correction flow + Day-22 handover

**Files:**
- Create: `backend/lms/lms/doctype/sales_trainee_attendance/__init__.py`
- Create: `backend/lms/lms/doctype/sales_trainee_attendance/sales_trainee_attendance.json`
- Create: `backend/lms/lms/doctype/sales_trainee_attendance/sales_trainee_attendance.py`
- Test: `backend/lms/lms/doctype/sales_trainee_attendance/test_sales_trainee_attendance.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2), `write_audit_log` (Task 3).
- Produces: DocType `Sales Trainee Attendance` (`trainee`, `attendance_date`, `status`, `source`, `marked_by`). Whitelisted method `mark(trainee, attendance_date, status, source="Manual")` (module-level, upsert by trainee+date) and doc method `correct(new_status, reason)` (whitelisted, writes an audit log). Both are what Task 8 (Zoom sync) and Task 13 (frontend) call.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/sales_trainee_attendance/test_sales_trainee_attendance.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark


class TestSalesTraineeAttendance(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Attendance Target",
				"personal_email": f"attendance-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_mark_creates_one_row(self):
		row = mark(self.trainee.name, "2026-10-06", "Present", source="Manual")
		self.assertEqual(row.status, "Present")
		self.assertEqual(row.source, "Manual")
		count = frappe.db.count(
			"Sales Trainee Attendance", {"trainee": self.trainee.name, "attendance_date": "2026-10-06"}
		)
		self.assertEqual(count, 1)

	def test_marking_same_trainee_date_twice_updates_not_duplicates(self):
		mark(self.trainee.name, "2026-10-07", "Present", source="Manual")
		mark(self.trainee.name, "2026-10-07", "Absent", source="Manual")
		rows = frappe.get_all(
			"Sales Trainee Attendance", filters={"trainee": self.trainee.name, "attendance_date": "2026-10-07"}
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(frappe.db.get_value("Sales Trainee Attendance", rows[0].name, "status"), "Absent")

	def test_correct_writes_audit_log_with_reason(self):
		row = mark(self.trainee.name, "2026-10-08", "Absent", source="Manual")
		row.correct("Present", reason="Trainee was present, marked absent by mistake")
		row.reload()
		self.assertEqual(row.status, "Present")
		logs = frappe.get_all(
			"Sales Trainee Audit Log",
			filters={"trainee": self.trainee.name, "field_changed": f"attendance:{row.name}"},
		)
		self.assertEqual(len(logs), 1)

	def test_correct_requires_reason(self):
		row = mark(self.trainee.name, "2026-10-09", "Absent", source="Manual")
		with self.assertRaises(frappe.MandatoryError):
			row.correct("Present", reason="")

	def test_correction_allowed_after_payroll_cycle_closed(self):
		# Review Focus: closing a cycle must not trap Training Team out of fixing a mistake.
		row = mark(self.trainee.name, "2026-10-10", "Absent", source="Manual")
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"status": "Closed",
			}
		).insert(ignore_permissions=True)
		row.correct("Present", reason="Late correction after cycle closed")
		row.reload()
		self.assertEqual(row.status, "Present")
		self.assertIn("Closed", cycle.status)  # cycle itself is untouched, correction just logs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_attendance.test_sales_trainee_attendance -v`
Expected: FAIL — DocType/module does not exist. (This test also needs `Weekly Payroll Cycle` from Task 5 — if running Task 4 before Task 5, skip `test_correction_allowed_after_payroll_cycle_closed` until Task 5 lands, or do Task 5 first. Recommended order: do Task 5 before running this specific test, or run Tasks 4 and 5 back to back before the full suite.)

- [ ] **Step 3: Create the DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["trainee", "attendance_date", "column_break_1", "status", "source", "marked_by"],
 "fields": [
  {"fieldname": "trainee", "fieldtype": "Link", "label": "Trainee", "options": "Sales Trainee", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "attendance_date", "fieldtype": "Date", "label": "Attendance Date", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "column_break_1", "fieldtype": "Column Break"},
  {"fieldname": "status", "fieldtype": "Select", "label": "Status", "reqd": 1, "in_list_view": 1, "options": "Present\nAbsent\nLeave\nHoliday"},
  {"fieldname": "source", "fieldtype": "Select", "label": "Source", "default": "Manual", "options": "Manual\nZoom Sync", "read_only": 1, "in_list_view": 1},
  {"fieldname": "marked_by", "fieldtype": "Link", "label": "Marked By", "options": "User", "read_only": 1}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Sales Trainee Attendance",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
  {"role": "Sales Training Team", "read": 1, "write": 1, "create": 1, "report": 1, "export": 1},
  {"role": "Sales Trainee Manager", "read": 1, "write": 1, "create": 1, "report": 1, "export": 1},
  {"role": "Sales Training Finance", "read": 1, "report": 1, "export": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "attendance_date",
 "sort_order": "DESC",
 "states": [],
 "title_field": "trainee",
 "autoname": "TA-.YYYY.-.#####",
 "naming_rule": "Expression (old style)",
 "track_changes": 1
}
```

- [ ] **Step 4: Create the controller with `mark()` and `correct()`**

```python
# backend/lms/lms/doctype/sales_trainee_attendance/sales_trainee_attendance.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log


class SalesTraineeAttendance(Document):
	def validate(self):
		if not self.marked_by:
			self.marked_by = frappe.session.user

	@frappe.whitelist()
	def correct(self, new_status, reason=None):
		"""Change status after the fact, always audit-logged. Allowed even after the
		owning Weekly Payroll Cycle has closed — Finance reconciles from the audit
		trail rather than being blocked from ever fixing a mistake."""
		if not (reason or "").strip():
			frappe.throw(_("A reason is required to correct attendance."), frappe.MandatoryError)
		old_status = self.status
		if old_status == new_status:
			return self
		write_audit_log(
			trainee=self.trainee,
			field_changed=f"attendance:{self.name}",
			old_value=old_status,
			new_value=new_status,
			reason=reason,
		)
		self.status = new_status
		self.save(ignore_permissions=True)
		return self


def mark(trainee, attendance_date, status, source="Manual", marked_by=None):
	"""Upsert one attendance row for trainee+date. Never creates a duplicate for the
	same (trainee, attendance_date) pair — a second call for the same day updates
	the existing row instead."""
	attendance_date = getdate(attendance_date)
	existing = frappe.db.get_value(
		"Sales Trainee Attendance", {"trainee": trainee, "attendance_date": attendance_date}, "name"
	)
	if existing:
		doc = frappe.get_doc("Sales Trainee Attendance", existing)
		doc.status = status
		doc.source = source
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Sales Trainee Attendance",
				"trainee": trainee,
				"attendance_date": attendance_date,
				"status": status,
				"source": source,
				"marked_by": marked_by or frappe.session.user,
			}
		)
	doc.save(ignore_permissions=True)
	return doc
```

```python
# backend/lms/lms/doctype/sales_trainee_attendance/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_attendance.test_sales_trainee_attendance -v`
Expected: PASS (5 tests, once Task 5's `Weekly Payroll Cycle` also exists)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee_attendance/
git commit -m "feat: add Sales Trainee Attendance with upsert-by-day marking and audited corrections"
```

---

### Task 5: Weekly Payroll Cycle + Weekly Payroll Input child DocType

**Files:**
- Create: `backend/lms/lms/doctype/weekly_payroll_input/__init__.py`
- Create: `backend/lms/lms/doctype/weekly_payroll_input/weekly_payroll_input.json`
- Create: `backend/lms/lms/doctype/weekly_payroll_input/weekly_payroll_input.py`
- Create: `backend/lms/lms/doctype/weekly_payroll_cycle/__init__.py`
- Create: `backend/lms/lms/doctype/weekly_payroll_cycle/weekly_payroll_cycle.json`
- Create: `backend/lms/lms/doctype/weekly_payroll_cycle/weekly_payroll_cycle.py`
- Test: `backend/lms/lms/doctype/weekly_payroll_cycle/test_weekly_payroll_cycle.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2), `Sales Trainee Cohort` (Task 1).
- Produces: DocType `Weekly Payroll Cycle` with child table `payroll_inputs` (`Weekly Payroll Input`, fields `trainee`, `salary`, `working_days`, `payable_days`, `joining_or_exit_adjustment_note`). Whitelisted doc method `advance_status(new_status)` enforcing the fixed status sequence. Task 9 populates `payroll_inputs` from attendance.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/weekly_payroll_cycle/test_weekly_payroll_cycle.py
import frappe
from frappe.tests import UnitTestCase


class TestWeeklyPayrollCycle(UnitTestCase):
	def test_create_cycle_defaults_to_preparing(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		)
		cycle.insert(ignore_permissions=True)
		self.assertEqual(cycle.status, "Preparing")

	def test_advance_status_follows_sequence(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		cycle.advance_status("Ready to Share")
		cycle.reload()
		self.assertEqual(cycle.status, "Ready to Share")

	def test_advance_status_rejects_skipping_a_step(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			cycle.advance_status("Closed")

	def test_payroll_input_child_rows(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Payroll Target",
				"personal_email": f"payroll-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"salary": 25000,
			}
		).insert(ignore_permissions=True)
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"payroll_inputs": [
					{"trainee": trainee.name, "salary": 25000, "working_days": 6, "payable_days": 6}
				],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(len(cycle.payroll_inputs), 1)
		self.assertEqual(cycle.payroll_inputs[0].payable_days, 6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.weekly_payroll_cycle.test_weekly_payroll_cycle -v`
Expected: FAIL — DocTypes do not exist.

- [ ] **Step 3: Create the child DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "istable": 1,
 "field_order": ["trainee", "salary", "working_days", "payable_days", "joining_or_exit_adjustment_note"],
 "fields": [
  {"fieldname": "trainee", "fieldtype": "Link", "label": "Trainee", "options": "Sales Trainee", "reqd": 1, "in_list_view": 1},
  {"fieldname": "salary", "fieldtype": "Currency", "label": "Salary", "in_list_view": 1},
  {"fieldname": "working_days", "fieldtype": "Int", "label": "Working Days", "in_list_view": 1},
  {"fieldname": "payable_days", "fieldtype": "Int", "label": "Payable Days", "in_list_view": 1},
  {"fieldname": "joining_or_exit_adjustment_note", "fieldtype": "Small Text", "label": "Joining/Exit Adjustment Note"}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Weekly Payroll Input",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

```python
# backend/lms/lms/doctype/weekly_payroll_input/weekly_payroll_input.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WeeklyPayrollInput(Document):
	pass
```

```python
# backend/lms/lms/doctype/weekly_payroll_input/__init__.py
```

- [ ] **Step 4: Create the `Weekly Payroll Cycle` DocType JSON**

```json
{
 "actions": [],
 "creation": "2026-09-24 00:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "week_start", "week_end", "cohort", "column_break_1", "status", "shared_on",
  "section_break_finance", "vendor_invoice_amount", "finance_validated_by", "finance_validated_on", "exceptions_notes",
  "section_break_inputs", "payroll_inputs"
 ],
 "fields": [
  {"fieldname": "week_start", "fieldtype": "Date", "label": "Week Start", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
  {"fieldname": "week_end", "fieldtype": "Date", "label": "Week End", "reqd": 1, "in_list_view": 1},
  {"fieldname": "cohort", "fieldtype": "Link", "label": "Cohort", "options": "Sales Trainee Cohort", "in_standard_filter": 1},
  {"fieldname": "column_break_1", "fieldtype": "Column Break"},
  {"fieldname": "status", "fieldtype": "Select", "label": "Status", "default": "Preparing", "in_list_view": 1, "in_standard_filter": 1, "read_only": 1,
   "options": "Preparing\nReady to Share\nShared with Vendor\nAwaiting Invoice\nFinance Validation\nClosed"},
  {"fieldname": "shared_on", "fieldtype": "Datetime", "label": "Shared On", "read_only": 1},
  {"fieldname": "section_break_finance", "fieldtype": "Section Break", "label": "Finance"},
  {"fieldname": "vendor_invoice_amount", "fieldtype": "Currency", "label": "Vendor Invoice Amount"},
  {"fieldname": "finance_validated_by", "fieldtype": "Link", "label": "Finance Validated By", "options": "User", "read_only": 1},
  {"fieldname": "finance_validated_on", "fieldtype": "Datetime", "label": "Finance Validated On", "read_only": 1},
  {"fieldname": "exceptions_notes", "fieldtype": "Small Text", "label": "Exceptions Notes"},
  {"fieldname": "section_break_inputs", "fieldtype": "Section Break", "label": "Trainee Inputs"},
  {"fieldname": "payroll_inputs", "fieldtype": "Table", "label": "Payroll Inputs", "options": "Weekly Payroll Input"}
 ],
 "index_web_pages_for_search": 0,
 "links": [],
 "modified": "2026-09-24 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "LMS",
 "name": "Weekly Payroll Cycle",
 "owner": "Administrator",
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
  {"role": "Sales Training Team", "read": 1, "create": 1, "write": 1, "report": 1},
  {"role": "Sales Trainee Manager", "read": 1, "report": 1},
  {"role": "Sales Training Finance", "read": 1, "write": 1, "report": 1, "export": 1},
  {"role": "Sales Training Leadership", "read": 1, "report": 1}
 ],
 "sort_field": "week_start",
 "sort_order": "DESC",
 "states": [],
 "title_field": "week_start",
 "autoname": "WPC-.YYYY.-.#####",
 "naming_rule": "Expression (old style)",
 "track_changes": 1
}
```

- [ ] **Step 5: Create the controller with `advance_status`**

```python
# backend/lms/lms/doctype/weekly_payroll_cycle/weekly_payroll_cycle.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

STATUS_SEQUENCE = [
	"Preparing",
	"Ready to Share",
	"Shared with Vendor",
	"Awaiting Invoice",
	"Finance Validation",
	"Closed",
]


class WeeklyPayrollCycle(Document):
	@frappe.whitelist()
	def advance_status(self, new_status):
		current_index = STATUS_SEQUENCE.index(self.status)
		try:
			target_index = STATUS_SEQUENCE.index(new_status)
		except ValueError:
			frappe.throw(_("{0} is not a valid payroll cycle status.").format(new_status))
		if target_index != current_index + 1:
			frappe.throw(
				_("Cannot move from {0} to {1} — cycles advance one step at a time.").format(
					self.status, new_status
				)
			)
		self.status = new_status
		if new_status == "Shared with Vendor":
			self.shared_on = now_datetime()
		if new_status == "Closed":
			self.finance_validated_by = frappe.session.user
			self.finance_validated_on = now_datetime()
		self.save(ignore_permissions=True)
		return self
```

```python
# backend/lms/lms/doctype/weekly_payroll_cycle/__init__.py
```

- [ ] **Step 6: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.weekly_payroll_cycle.test_weekly_payroll_cycle -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/lms/lms/doctype/weekly_payroll_input/ backend/lms/lms/doctype/weekly_payroll_cycle/
git commit -m "feat: add Weekly Payroll Cycle with status sequence and per-trainee input rows"
```

---

### Task 6: Trainee visibility scoping (`trainee_scope.py`)

**Files:**
- Create: `backend/lms/lms/trainee_scope.py`
- Create: `backend/lms/lms/test_trainee_scope.py`
- Modify: `backend/lms/hooks.py`

**Interfaces:**
- Consumes: `access.reporting_tree(root, lines)` and `access.is_admin(user)` from `backend/lms/lms/access.py` (existing); `Sales Trainee` (Task 2).
- Produces: `sales_trainee_query_conditions(user=None)` and `sales_trainee_has_permission(doc, ptype=None, user=None)`, registered in `hooks.py` for `Sales Trainee` and `Sales Trainee Attendance`.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_scope.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_scope import sales_trainee_query_conditions


class TestTraineeScope(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.manager = self._get_or_create_user("trainee-scope-manager@example.com")
		self.other_manager = self._get_or_create_user("trainee-scope-other-manager@example.com")
		self.trainee_with_manager = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Managed Trainee",
				"personal_email": f"managed-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_sales_manager": self.manager,
			}
		).insert(ignore_permissions=True)
		self.trainee_no_manager_yet = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Unassigned Trainee",
				"personal_email": f"unassigned-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_trainer": self.manager,
			}
		).insert(ignore_permissions=True)

	def _get_or_create_user(self, email):
		if frappe.db.exists("User", email):
			return email
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0]}).insert(
			ignore_permissions=True
		)
		return email

	def test_manager_sees_assigned_trainee(self):
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608 - condition is server-built, not user input
		)
		names = {row.name for row in visible}
		self.assertIn(self.trainee_with_manager.name, names)

	def test_manager_does_not_see_unrelated_trainee(self):
		other_trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Someone Else's Trainee",
				"personal_email": f"else-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"assigned_sales_manager": self.other_manager,
			}
		).insert(ignore_permissions=True)
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608
		)
		names = {row.name for row in visible}
		self.assertNotIn(other_trainee.name, names)

	def test_unassigned_manager_still_sees_own_trainer_assignment(self):
		# Review Focus: a Day-1 trainee with no assigned_sales_manager yet must not
		# vanish from everyone's view — their assigned_trainer must still see them.
		condition = sales_trainee_query_conditions(self.manager)
		visible = frappe.db.sql(
			f"select name from `tabSales Trainee` where {condition}", as_dict=True  # noqa: S608
		)
		names = {row.name for row in visible}
		self.assertIn(self.trainee_no_manager_yet.name, names)

	def test_admin_sees_everything(self):
		condition = sales_trainee_query_conditions("Administrator")
		self.assertEqual(condition, "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_scope -v`
Expected: FAIL — `lms.lms.trainee_scope` does not exist.

- [ ] **Step 3: Implement `trainee_scope.py`**

```python
# backend/lms/lms/trainee_scope.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe

from lms.lms import access

FINANCE_AND_LEADERSHIP_ROLES = {"Sales Training Finance", "Sales Training Leadership"}


def _active_reporting_lines():
	return [
		(row.member, row.manager)
		for row in frappe.get_all("LMS Reporting Line", filters={"status": "Active"}, fields=["member", "manager"])
	]


def _sees_everything(user):
	if access.is_admin(user):
		return True
	roles = set(frappe.get_roles(user))
	return bool(roles & FINANCE_AND_LEADERSHIP_ROLES)


def sales_trainee_query_conditions(user=None):
	"""Scope Sales Trainee / Sales Trainee Attendance visibility to a manager's own
	reporting tree, keyed by assigned_sales_manager / assigned_trainer rather than
	a Link->User on the trainee itself (the trainee has none). A trainee with no
	assigned_sales_manager yet still shows up via assigned_trainer, so a fresh
	Day-1 onboard is never invisible to everyone."""
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	escaped = ", ".join(frappe.db.escape(u) for u in visible_users)
	return (
		f"(`tabSales Trainee`.assigned_sales_manager in ({escaped}) "
		f"or `tabSales Trainee`.assigned_trainer in ({escaped}))"
	)


def sales_trainee_attendance_query_conditions(user=None):
	"""Same scoping as sales_trainee_query_conditions, joined through the trainee."""
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	escaped = ", ".join(frappe.db.escape(u) for u in visible_users)
	return (
		f"`tabSales Trainee Attendance`.trainee in ("
		f"select name from `tabSales Trainee` where assigned_sales_manager in ({escaped}) "
		f"or assigned_trainer in ({escaped}))"
	)


def sales_trainee_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _sees_everything(user):
		return True
	lines = _active_reporting_lines()
	visible_users = access.reporting_tree(user, lines) | {user}
	trainee_doc = doc if doc.doctype == "Sales Trainee" else frappe.get_cached_doc("Sales Trainee", doc.trainee)
	return trainee_doc.assigned_sales_manager in visible_users or trainee_doc.assigned_trainer in visible_users
```

- [ ] **Step 4: Register in `hooks.py`**

```python
# backend/lms/hooks.py
# In the existing permission_query_conditions dict, add:
	"Sales Trainee": "lms.lms.trainee_scope.sales_trainee_query_conditions",
	"Sales Trainee Attendance": "lms.lms.trainee_scope.sales_trainee_attendance_query_conditions",

# In the existing has_permission dict, add:
	"Sales Trainee": "lms.lms.trainee_scope.sales_trainee_has_permission",
	"Sales Trainee Attendance": "lms.lms.trainee_scope.sales_trainee_has_permission",
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_scope -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/trainee_scope.py backend/lms/lms/test_trainee_scope.py backend/lms/hooks.py
git commit -m "feat: scope trainee/attendance visibility to a manager's reporting tree"
```

---

### Task 7: Bulk onboarding import (`sales_trainee_import.py`)

**Files:**
- Create: `backend/lms/lms/sales_trainee_import.py`
- Create: `backend/lms/lms/test_sales_trainee_import.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2), `Sales Trainee Cohort` (Task 1).
- Produces: `@frappe.whitelist(methods=["POST"]) def import_sales_trainees(rows, dry_run=True)` — `rows` is a list of dicts with keys `trainee_name`, `personal_email`, `phone`, `location`, `date_of_joining`, `salary`, `cohort`, `ta_spoc`. Returns `{"ok": bool, "errors": [...], "created": int, "updated": int}`. Used by Task 11 (frontend import screen).

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_sales_trainee_import.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.sales_trainee_import import import_sales_trainees


class TestSalesTraineeImport(UnitTestCase):
	def _row(self, email, **overrides):
		row = {
			"trainee_name": "Import Target",
			"personal_email": email,
			"phone": "9999999999",
			"date_of_joining": "2026-10-06",
		}
		row.update(overrides)
		return row

	def test_dry_run_flags_missing_mandatory_field(self):
		result = import_sales_trainees(
			rows=[{"trainee_name": "No Email", "date_of_joining": "2026-10-06"}], dry_run=True
		)
		self.assertFalse(result["ok"])
		self.assertTrue(any("personal_email" in e for e in result["errors"]))
		self.assertFalse(frappe.db.exists("Sales Trainee", {"trainee_name": "No Email"}))

	def test_dry_run_flags_duplicate_rows_in_same_batch(self):
		email = f"dupe-{frappe.generate_hash(length=6)}@example.com"
		result = import_sales_trainees(rows=[self._row(email), self._row(email)], dry_run=True)
		self.assertFalse(result["ok"])
		self.assertTrue(any("duplicate" in e.lower() for e in result["errors"]))

	def test_real_run_creates_trainee(self):
		email = f"create-{frappe.generate_hash(length=6)}@example.com"
		result = import_sales_trainees(rows=[self._row(email)], dry_run=False)
		self.assertTrue(result["ok"])
		self.assertEqual(result["created"], 1)
		self.assertTrue(frappe.db.exists("Sales Trainee", {"personal_email": email}))

	def test_re_upload_of_existing_email_updates_not_duplicates(self):
		# Review Focus: re-uploading (or moving cohort) must upsert, never create a
		# second Sales Trainee for the same person.
		email = f"reupload-{frappe.generate_hash(length=6)}@example.com"
		import_sales_trainees(rows=[self._row(email, location="Pune")], dry_run=False)
		result = import_sales_trainees(rows=[self._row(email, location="Bengaluru")], dry_run=False)
		self.assertTrue(result["ok"])
		self.assertEqual(result["updated"], 1)
		matches = frappe.get_all("Sales Trainee", filters={"personal_email": email})
		self.assertEqual(len(matches), 1)
		self.assertEqual(frappe.db.get_value("Sales Trainee", matches[0].name, "location"), "Bengaluru")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_sales_trainee_import -v`
Expected: FAIL — `lms.lms.sales_trainee_import` does not exist.

- [ ] **Step 3: Implement `sales_trainee_import.py`**

```python
# backend/lms/lms/sales_trainee_import.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

MANDATORY_FIELDS = ("trainee_name", "personal_email", "date_of_joining")


def _row_key(personal_email):
	return (personal_email or "").strip().lower()


def _validate_rows(rows):
	errors = []
	seen_keys = set()
	for i, row in enumerate(rows, start=1):
		for field in MANDATORY_FIELDS:
			if not (row.get(field) or "").strip() if isinstance(row.get(field), str) else not row.get(field):
				errors.append(f"Row {i}: missing mandatory field '{field}'")
		key = _row_key(row.get("personal_email"))
		if key:
			if key in seen_keys:
				errors.append(f"Row {i}: duplicate personal_email '{row.get('personal_email')}' within this upload")
			seen_keys.add(key)
	return errors


@frappe.whitelist(methods=["POST"])
def import_sales_trainees(rows, dry_run=True):
	"""Bulk upsert Sales Trainee records, deduped by personal_email — same shape as
	ojt_certification.py's row-key upsert. dry_run=True validates only, never writes."""
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() in ("1", "true", "yes")
	errors = _validate_rows(rows)
	if errors:
		return {"ok": False, "errors": errors, "created": 0, "updated": 0}
	if dry_run:
		return {"ok": True, "errors": [], "created": 0, "updated": 0}

	created, updated = 0, 0
	row_errors = []
	for i, row in enumerate(rows, start=1):
		try:
			key = _row_key(row.get("personal_email"))
			existing = frappe.db.get_value("Sales Trainee", {"personal_email": key}, "name")
			if existing:
				doc = frappe.get_doc("Sales Trainee", existing)
				updated += 1
			else:
				doc = frappe.new_doc("Sales Trainee")
				created += 1
			doc.trainee_name = row.get("trainee_name")
			doc.personal_email = key
			doc.phone = row.get("phone")
			doc.location = row.get("location")
			doc.date_of_joining = getdate(row.get("date_of_joining"))
			doc.salary = row.get("salary")
			doc.cohort = row.get("cohort")
			doc.ta_spoc = row.get("ta_spoc")
			doc.save(ignore_permissions=True)
		except Exception as e:  # noqa: BLE001 - one bad row must not sink the batch
			row_errors.append(f"Row {i}: {e}")
	frappe.db.commit()
	if row_errors:
		return {"ok": False, "errors": row_errors, "created": created, "updated": updated}
	return {"ok": True, "errors": [], "created": created, "updated": updated}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_sales_trainee_import -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/sales_trainee_import.py backend/lms/lms/test_sales_trainee_import.py
git commit -m "feat: add bulk trainee onboarding with email-keyed upsert"
```

---

### Task 8: Zoom live-class attendance sync bridge

**Files:**
- Create: `backend/lms/lms/trainee_attendance_sync.py`
- Create: `backend/lms/lms/test_trainee_attendance_sync.py`
- Modify: `backend/lms/hooks.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2, matched by `personal_email`), `mark()` from Task 4.
- Produces: `sync_from_live_class_participant(doc, event)` registered as a `doc_events["LMS Live Class Participant"]["after_insert"]` hook.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_attendance_sync.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_attendance_sync import sync_from_live_class_participant


class TestTraineeAttendanceSync(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.email = f"zoom-crt-{frappe.generate_hash(length=6)}@example.com"
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Zoom Synced Trainee",
				"personal_email": self.email,
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_matching_participant_creates_zoom_sourced_attendance(self):
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": self.email,
				"joined_at": "2026-10-06 09:00:00",
				"left_at": "2026-10-06 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_mandatory = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")
		row = frappe.db.get_value(
			"Sales Trainee Attendance",
			{"trainee": self.trainee.name, "attendance_date": "2026-10-06"},
			["status", "source"],
			as_dict=True,
		)
		self.assertIsNotNone(row)
		self.assertEqual(row.status, "Present")
		self.assertEqual(row.source, "Zoom Sync")

	def test_non_matching_participant_is_a_no_op(self):
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": "not-a-trainee@example.com",
				"joined_at": "2026-10-06 09:00:00",
				"left_at": "2026-10-06 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_mandatory = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")  # must not raise
		count = frappe.db.count("Sales Trainee Attendance", {"attendance_date": "2026-10-06"})
		self.assertEqual(count, 0)

	def test_existing_manual_entry_for_same_day_is_not_overwritten(self):
		from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark

		mark(self.trainee.name, "2026-10-07", "Absent", source="Manual")
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": self.email,
				"joined_at": "2026-10-07 09:00:00",
				"left_at": "2026-10-07 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_mandatory = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")
		status = frappe.db.get_value(
			"Sales Trainee Attendance", {"trainee": self.trainee.name, "attendance_date": "2026-10-07"}, "status"
		)
		self.assertEqual(status, "Absent")  # manual entry wins; Zoom sync does not clobber a correction
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_attendance_sync -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `trainee_attendance_sync.py`**

```python
# backend/lms/lms/trainee_attendance_sync.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark


def sync_from_live_class_participant(doc, event=None):
	"""Bridge the existing Zoom-based live-class attendance sync into the trainee
	attendance ledger. Matches by personal_email since Sales Trainee has no User
	link. A pre-existing Manual row for the same day is left untouched — Zoom sync
	never clobbers a staff correction."""
	email = (doc.member or "").strip().lower()
	if not email:
		return
	trainee = frappe.db.get_value("Sales Trainee", {"personal_email": email}, "name")
	if not trainee:
		return
	attendance_date = getdate(doc.joined_at)
	existing = frappe.db.get_value(
		"Sales Trainee Attendance", {"trainee": trainee, "attendance_date": attendance_date}, ["name", "source"], as_dict=True
	)
	if existing and existing.source == "Manual":
		return
	mark(trainee, attendance_date, "Present", source="Zoom Sync", marked_by="Administrator")
```

- [ ] **Step 4: Register in `hooks.py`**

```python
# backend/lms/hooks.py
# In the existing doc_events dict, add:
	"LMS Live Class Participant": {
		"after_insert": "lms.lms.trainee_attendance_sync.sync_from_live_class_participant",
	},
```

- [ ] **Step 5: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_attendance_sync -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/trainee_attendance_sync.py backend/lms/lms/test_trainee_attendance_sync.py backend/lms/hooks.py
git commit -m "feat: bridge existing Zoom live-class attendance into trainee attendance ledger"
```

---

### Task 9: Payable-days computation + weekly payroll input prep

**Files:**
- Create: `backend/lms/lms/trainee_payroll.py`
- Create: `backend/lms/lms/test_trainee_payroll.py`

**Interfaces:**
- Consumes: `Sales Trainee` (Task 2), `Sales Trainee Attendance` (Task 4), `Weekly Payroll Cycle`/`Weekly Payroll Input` (Task 5).
- Produces: `compute_payable_days(trainee, week_start, week_end)` and `@frappe.whitelist(methods=["POST"]) def prepare_weekly_inputs(cycle_name)` (fills `payroll_inputs` on the cycle from attendance + trainee salary; used by Task 14's Finance screen).

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_payroll.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.trainee_payroll import compute_payable_days, prepare_weekly_inputs


class TestTraineePayroll(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Payable Days Target",
				"personal_email": f"payable-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"salary": 21000,
			}
		).insert(ignore_permissions=True)
		for day in range(6, 13):  # Oct 6-12
			status = "Present" if day != 9 else "Absent"
			mark(self.trainee.name, f"2026-10-{day:02d}", status, source="Manual")

	def test_compute_payable_days_counts_present_only(self):
		payable = compute_payable_days(self.trainee.name, "2026-10-06", "2026-10-12")
		self.assertEqual(payable, 6)  # 7 days marked, 1 Absent

	def test_compute_payable_days_stops_at_exit_date(self):
		# Review Focus: exiting mid-week must not count days after exit_date.
		self.trainee.exit_date = "2026-10-09"
		self.trainee.training_status = "Resigned"
		self.trainee.exit_status = "Resigned"
		self.trainee.save(ignore_permissions=True)
		payable = compute_payable_days(self.trainee.name, "2026-10-06", "2026-10-12")
		self.assertEqual(payable, 2)  # Oct 6,7,8 present, Oct 9 absent+exit, nothing after counts

	def test_prepare_weekly_inputs_fills_child_table(self):
		cycle = frappe.get_doc(
			{"doctype": "Weekly Payroll Cycle", "week_start": "2026-10-06", "week_end": "2026-10-12"}
		).insert(ignore_permissions=True)
		result = prepare_weekly_inputs(cycle.name)
		self.assertTrue(result["ok"])
		cycle.reload()
		row = next(r for r in cycle.payroll_inputs if r.trainee == self.trainee.name)
		self.assertEqual(row.payable_days, 6)
		self.assertEqual(row.salary, 21000)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_payroll -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `trainee_payroll.py`**

```python
# backend/lms/lms/trainee_payroll.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate


def compute_payable_days(trainee, week_start, week_end):
	"""Count Present days for trainee in [week_start, week_end], never counting past
	exit_date if the trainee exited mid-week."""
	week_start, week_end = getdate(week_start), getdate(week_end)
	exit_date = frappe.db.get_value("Sales Trainee", trainee, "exit_date")
	effective_end = min(week_end, getdate(exit_date)) if exit_date else week_end
	if effective_end < week_start:
		return 0
	return frappe.db.count(
		"Sales Trainee Attendance",
		{
			"trainee": trainee,
			"attendance_date": ["between", [week_start, effective_end]],
			"status": "Present",
		},
	)


@frappe.whitelist(methods=["POST"])
def prepare_weekly_inputs(cycle_name):
	"""Populate payroll_inputs on a Weekly Payroll Cycle from attendance + current
	trainee salary. Capture-only: does not compute a pro-rata amount (spec §2)."""
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	filters = {"training_status": "In Training"}
	if cycle.cohort:
		filters["cohort"] = cycle.cohort
	trainees = frappe.get_all("Sales Trainee", filters=filters, fields=["name", "salary", "date_of_joining"])
	cycle.payroll_inputs = []
	for t in trainees:
		effective_start = max(getdate(cycle.week_start), getdate(t.date_of_joining))
		working_days = max((getdate(cycle.week_end) - effective_start).days + 1, 0)
		payable_days = compute_payable_days(t.name, cycle.week_start, cycle.week_end)
		cycle.append(
			"payroll_inputs",
			{"trainee": t.name, "salary": t.salary, "working_days": working_days, "payable_days": payable_days},
		)
	cycle.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "trainee_count": len(trainees)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_payroll -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/trainee_payroll.py backend/lms/lms/test_trainee_payroll.py
git commit -m "feat: compute payable days from attendance and prep weekly payroll inputs"
```

---

### Task 10: Report/export endpoints

**Files:**
- Create: `backend/lms/lms/trainee_reports.py`
- Test: `backend/lms/lms/test_trainee_reports.py`

**Interfaces:**
- Consumes: `Sales Trainee`, `Sales Trainee Attendance`, `Weekly Payroll Cycle` (Tasks 2, 4, 5).
- Produces: `@frappe.whitelist() def export_active_trainees_csv(cohort=None, location=None)` returning a base64-encoded XLSX via `openpyxl`, following the pattern of existing report exports in this app. Used by Task 14.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_reports.py
import base64
import io

import frappe
import openpyxl
from frappe.tests import UnitTestCase

from lms.lms.trainee_reports import export_active_trainees_csv


class TestTraineeReports(UnitTestCase):
	def test_export_includes_only_in_training_trainees(self):
		active = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Active One",
				"personal_email": f"active-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		exited = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exited One",
				"personal_email": f"exited-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "Resigned",
			}
		).insert(ignore_permissions=True)

		encoded = export_active_trainees_csv()
		workbook = openpyxl.load_workbook(io.BytesIO(base64.b64decode(encoded)))
		sheet = workbook.active
		names_in_sheet = {row[0].value for row in sheet.iter_rows(min_row=2)}
		self.assertIn(active.trainee_name, names_in_sheet)
		self.assertNotIn(exited.trainee_name, names_in_sheet)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_reports -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `trainee_reports.py`**

```python
# backend/lms/lms/trainee_reports.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import base64
import io

import frappe
import openpyxl


@frappe.whitelist()
def export_active_trainees_csv(cohort=None, location=None):
	"""Active Trainee Report (spec §9) as a base64-encoded XLSX."""
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	if location:
		filters["location"] = location
	rows = frappe.get_all(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "personal_email", "location", "cohort", "date_of_joining", "employee_dummy_vendor_code"],
		order_by="date_of_joining asc",
	)
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = "Active Trainees"
	sheet.append(["Trainee Name", "Personal Email", "Location", "Cohort", "Date of Joining", "Employee/Dummy/Vendor Code"])
	for row in rows:
		sheet.append(
			[row.trainee_name, row.personal_email, row.location, row.cohort, str(row.date_of_joining or ""), row.employee_dummy_vendor_code]
		)
	buffer = io.BytesIO()
	workbook.save(buffer)
	return base64.b64encode(buffer.getvalue()).decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_reports -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/trainee_reports.py backend/lms/lms/test_trainee_reports.py
git commit -m "feat: add Active Trainee Report XLSX export"
```

---

### Task 11: Frontend — bulk onboarding screen

**Files:**
- Create: `frontend/src/pages/Sales/TraineeImport.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/utils/index.js`

**Interfaces:**
- Consumes: `lms.lms.sales_trainee_import.import_sales_trainees` (Task 7).
- Produces: route `TraineeImport` at `/sales-trainees/import`.

- [ ] **Step 1: Add the route**

```javascript
// frontend/src/router.js
// Near the existing SalesImport route (~line 88-92), add:
{
	path: '/sales-trainees/import',
	name: 'TraineeImport',
	component: () => import('@/pages/Sales/TraineeImport.vue'),
},
```

Also add `'TraineeImport'` to the existing `staffOnlyRoutes` array (~line 505).

- [ ] **Step 2: Build the screen, mirroring `SalesImport.vue`'s upload/dry-run/commit flow**

```vue
<!-- frontend/src/pages/Sales/TraineeImport.vue -->
<template>
	<div class="p-6 max-w-3xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Bulk Onboard Sales Trainees</h1>
		<input ref="fileInput" type="file" accept=".csv" class="mb-4" @change="onFileSelected" />
		<div class="flex gap-2 mb-4">
			<Button :loading="busy" @click="runImport(true)">Validate (dry run)</Button>
			<Button :loading="busy" variant="solid" :disabled="!preview?.ok" @click="runImport(false)">
				Import
			</Button>
		</div>
		<div v-if="error" class="text-red-600 mb-4">{{ error }}</div>
		<div v-if="preview">
			<p v-if="preview.ok" class="text-green-700">
				Looks good — {{ rows.length }} rows ready to import.
			</p>
			<ul v-else class="text-red-600 list-disc pl-5">
				<li v-for="(e, i) in preview.errors" :key="i">{{ e }}</li>
			</ul>
		</div>
		<div v-if="result" class="mt-4">
			<p class="text-green-700">
				Created {{ result.created }}, updated {{ result.updated }}.
			</p>
			<ul v-if="result.errors?.length" class="text-red-600 list-disc pl-5">
				<li v-for="(e, i) in result.errors" :key="i">{{ e }}</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { call, Button } from 'frappe-ui'

const fileInput = ref(null)
const rows = ref([])
const preview = ref(null)
const result = ref(null)
const error = ref('')
const busy = ref(false)

function onFileSelected(e) {
	const file = e.target.files[0]
	if (!file) return
	const reader = new FileReader()
	reader.onload = () => {
		rows.value = parseCsv(reader.result)
	}
	reader.readAsText(file)
}

function parseCsv(text) {
	const [headerLine, ...lines] = text.trim().split('\n')
	const headers = headerLine.split(',').map((h) => h.trim())
	return lines
		.filter((l) => l.trim())
		.map((line) => {
			const values = line.split(',')
			return Object.fromEntries(headers.map((h, i) => [h, (values[i] || '').trim()]))
		})
}

async function runImport(dryRun) {
	error.value = ''
	busy.value = true
	try {
		const response = await call('lms.lms.sales_trainee_import.import_sales_trainees', {
			rows: rows.value,
			dry_run: dryRun,
		})
		if (dryRun) {
			preview.value = response
		} else {
			result.value = response
		}
	} catch (err) {
		error.value = err?.messages?.[0] || err?.message || 'Import failed'
	} finally {
		busy.value = false
	}
}
</script>
```

- [ ] **Step 3: Add the nav entry**

```javascript
// frontend/src/utils/index.js
// In the same array as the existing 'Team & access' entry, add:
{
	label: 'Trainee onboarding',
	icon: 'UserPlus',
	to: 'TraineeImport',
	activeFor: ['TraineeImport'],
	condition: () => {
		const tier = userResource?.data?.access_tier
		const roles = userResource?.data?.roles || []
		return !forMobile && (['Admin', 'Super Admin'].includes(tier) || roles.includes('Sales Training Team'))
	},
},
```

- [ ] **Step 4: Manually verify**

Run `yarn dev` (or the project's documented frontend dev command) inside `frontend/`, log in as a user with the `Sales Training Team` role, navigate to `/sales-trainees/import`, upload a CSV with header `trainee_name,personal_email,phone,location,date_of_joining,salary,cohort,ta_spoc` and at least one data row, click "Validate (dry run)" and confirm it reports 0 errors, then click "Import" and confirm the success count matches the row count. No automated frontend test exists in this repo (Cypress covers only a few flows) — this is a manual smoke check.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Sales/TraineeImport.vue frontend/src/router.js frontend/src/utils/index.js
git commit -m "feat: add bulk trainee onboarding screen"
```

---

### Task 12: Frontend — Cohort & Trainee list/detail screens

**Files:**
- Create: `frontend/src/pages/Sales/TraineeCohortList.vue`
- Create: `frontend/src/pages/Sales/TraineeList.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/utils/index.js`

**Interfaces:**
- Consumes: Frappe's generic list/resource API (`frappe-ui`'s `createListResource`) against `Sales Trainee Cohort` and `Sales Trainee` — no new backend endpoint needed, standard doctype list permissions (Task 1, 2, 6) already gate visibility.

- [ ] **Step 1: Add routes**

```javascript
// frontend/src/router.js
{
	path: '/sales-trainees/cohorts',
	name: 'TraineeCohortList',
	component: () => import('@/pages/Sales/TraineeCohortList.vue'),
},
{
	path: '/sales-trainees',
	name: 'TraineeList',
	component: () => import('@/pages/Sales/TraineeList.vue'),
},
```

Add both to `staffOnlyRoutes`.

- [ ] **Step 2: Build `TraineeCohortList.vue`**

```vue
<!-- frontend/src/pages/Sales/TraineeCohortList.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Cohorts</h1>
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Cohort</th>
					<th>Location</th>
					<th>Start Date</th>
					<th>Trainer</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="c in cohorts.data" :key="c.name" class="border-b">
					<td class="py-2">
						<router-link :to="{ name: 'TraineeList', query: { cohort: c.name } }">
							{{ c.cohort_name }}
						</router-link>
					</td>
					<td>{{ c.location }}</td>
					<td>{{ c.start_date }}</td>
					<td>{{ c.trainer }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { createListResource } from 'frappe-ui'

const cohorts = createListResource({
	doctype: 'Sales Trainee Cohort',
	fields: ['name', 'cohort_name', 'location', 'start_date', 'trainer'],
	auto: true,
	pageLength: 100,
})
</script>
```

- [ ] **Step 3: Build `TraineeList.vue`**

```vue
<!-- frontend/src/pages/Sales/TraineeList.vue -->
<template>
	<div class="p-6 max-w-5xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainees{{ cohortFilter ? ` — ${cohortFilter}` : '' }}</h1>
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Name</th>
					<th>Email</th>
					<th>Status</th>
					<th>DOJ</th>
					<th>Code</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="t in trainees.data" :key="t.name" class="border-b">
					<td class="py-2">{{ t.trainee_name }}</td>
					<td>{{ t.personal_email }}</td>
					<td>{{ t.training_status }}</td>
					<td>{{ t.date_of_joining }}</td>
					<td>{{ t.employee_dummy_vendor_code || '—' }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { createListResource } from 'frappe-ui'

const route = useRoute()
const cohortFilter = computed(() => route.query.cohort || '')

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name', 'personal_email', 'training_status', 'date_of_joining', 'employee_dummy_vendor_code'],
	filters: cohortFilter.value ? { cohort: cohortFilter.value } : {},
	auto: true,
	pageLength: 100,
})
</script>
```

- [ ] **Step 4: Add nav entries**

```javascript
// frontend/src/utils/index.js
{
	label: 'Trainees',
	icon: 'Users',
	to: 'TraineeList',
	activeFor: ['TraineeList', 'TraineeCohortList'],
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

- [ ] **Step 5: Manually verify**

Log in as a `Sales Trainee Manager`, visit `/sales-trainees`, confirm only trainees assigned to that manager (or their reports) appear — cross-check against Task 6's scoping. Visit `/sales-trainees/cohorts`, click through to a cohort's trainee list, confirm the `cohort` query filter works.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Sales/TraineeCohortList.vue frontend/src/pages/Sales/TraineeList.vue frontend/src/router.js frontend/src/utils/index.js
git commit -m "feat: add cohort and trainee list screens"
```

---

### Task 13: Frontend — Attendance marking screen

**Files:**
- Create: `frontend/src/pages/Sales/TraineeAttendance.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/utils/index.js`

**Interfaces:**
- Consumes: `mark()` via a thin whitelisted wrapper (add below), `correct()` doc method (Task 4).

- [ ] **Step 1: Add a whitelisted wrapper for `mark()` callable from the frontend**

```python
# backend/lms/lms/doctype/sales_trainee_attendance/sales_trainee_attendance.py
# Add below the existing mark() function:

@frappe.whitelist(methods=["POST"])
def mark_attendance(trainee, attendance_date, status):
	return mark(trainee, attendance_date, status, source="Manual").as_dict()
```

Add a matching test in `test_sales_trainee_attendance.py`:

```python
	def test_mark_attendance_whitelisted_wrapper(self):
		from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark_attendance

		result = mark_attendance(self.trainee.name, "2026-10-11", "Present")
		self.assertEqual(result["status"], "Present")
```

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee_attendance.test_sales_trainee_attendance -v` — expect PASS (6 tests total now).

- [ ] **Step 2: Add the route**

```javascript
// frontend/src/router.js
{
	path: '/sales-trainees/attendance',
	name: 'TraineeAttendance',
	component: () => import('@/pages/Sales/TraineeAttendance.vue'),
},
```

Add to `staffOnlyRoutes`.

- [ ] **Step 3: Build the screen**

```vue
<!-- frontend/src/pages/Sales/TraineeAttendance.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-2">Mark Attendance</h1>
		<input v-model="date" type="date" class="mb-4 border rounded px-2 py-1" />
		<table class="w-full text-left border-collapse">
			<thead>
				<tr class="border-b">
					<th class="py-2">Trainee</th>
					<th>Present</th>
					<th>Absent</th>
					<th>Leave</th>
					<th>Holiday</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="t in trainees.data" :key="t.name" class="border-b">
					<td class="py-2">{{ t.trainee_name }}</td>
					<td v-for="status in ['Present', 'Absent', 'Leave', 'Holiday']" :key="status">
						<input
							type="radio"
							:name="t.name"
							:checked="statusFor(t.name) === status"
							@change="setStatus(t.name, status)"
						/>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { call, createListResource } from 'frappe-ui'

const date = ref(new Date().toISOString().slice(0, 10))
const marked = ref({})

const trainees = createListResource({
	doctype: 'Sales Trainee',
	fields: ['name', 'trainee_name'],
	filters: { training_status: 'In Training' },
	auto: true,
	pageLength: 200,
})

function statusFor(trainee) {
	return marked.value[trainee]
}

async function setStatus(trainee, status) {
	marked.value[trainee] = status
	await call('lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance.mark_attendance', {
		trainee,
		attendance_date: date.value,
		status,
	})
}

watch(date, () => {
	marked.value = {}
})
</script>
```

- [ ] **Step 4: Add nav entry**

```javascript
// frontend/src/utils/index.js
{
	label: 'Mark attendance',
	icon: 'CalendarCheck',
	to: 'TraineeAttendance',
	activeFor: ['TraineeAttendance'],
	condition: () => {
		const roles = userResource?.data?.roles || []
		return !forMobile && (roles.includes('Sales Training Team') || roles.includes('Sales Trainee Manager'))
	},
},
```

- [ ] **Step 5: Manually verify**

Log in as `Sales Training Team`, visit `/sales-trainees/attendance`, mark a trainee Present for today, reload, confirm the radio reflects the saved state by cross-checking the `Sales Trainee Attendance` list view in the Frappe desk (`/app/sales-trainee-attendance`).

- [ ] **Step 6: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee_attendance/ frontend/src/pages/Sales/TraineeAttendance.vue frontend/src/router.js frontend/src/utils/index.js
git commit -m "feat: add manual attendance marking screen"
```

---

### Task 14: Frontend — Weekly Payroll Cycle (Finance) screen + dashboard

**Files:**
- Create: `frontend/src/pages/Sales/WeeklyPayrollCycle.vue`
- Create: `frontend/src/pages/Sales/TraineeDashboard.vue`
- Modify: `frontend/src/router.js`
- Modify: `frontend/src/utils/index.js`

**Interfaces:**
- Consumes: `prepare_weekly_inputs` (Task 9), `advance_status` doc method (Task 5), `export_active_trainees_csv` (Task 10).

- [ ] **Step 1: Add routes**

```javascript
// frontend/src/router.js
{
	path: '/sales-trainees/payroll',
	name: 'WeeklyPayrollCycle',
	component: () => import('@/pages/Sales/WeeklyPayrollCycle.vue'),
},
{
	path: '/sales-trainees/dashboard',
	name: 'TraineeDashboard',
	component: () => import('@/pages/Sales/TraineeDashboard.vue'),
},
```

Add both to `staffOnlyRoutes`.

- [ ] **Step 2: Build `WeeklyPayrollCycle.vue`**

```vue
<!-- frontend/src/pages/Sales/WeeklyPayrollCycle.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Weekly Payroll Cycles</h1>
		<table class="w-full text-left border-collapse mb-6">
			<thead>
				<tr class="border-b">
					<th class="py-2">Week</th>
					<th>Status</th>
					<th>Vendor Invoice</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="c in cycles.data" :key="c.name" class="border-b">
					<td class="py-2">{{ c.week_start }} – {{ c.week_end }}</td>
					<td>{{ c.status }}</td>
					<td>{{ c.vendor_invoice_amount || '—' }}</td>
					<td>
						<Button size="sm" @click="prepInputs(c.name)">Prepare Inputs</Button>
						<Button size="sm" @click="advance(c.name, nextStatus(c.status))" v-if="nextStatus(c.status)">
							Advance to {{ nextStatus(c.status) }}
						</Button>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { call, createListResource, Button } from 'frappe-ui'

const SEQUENCE = ['Preparing', 'Ready to Share', 'Shared with Vendor', 'Awaiting Invoice', 'Finance Validation', 'Closed']

const cycles = createListResource({
	doctype: 'Weekly Payroll Cycle',
	fields: ['name', 'week_start', 'week_end', 'status', 'vendor_invoice_amount'],
	auto: true,
	pageLength: 50,
})

function nextStatus(current) {
	const i = SEQUENCE.indexOf(current)
	return i >= 0 && i < SEQUENCE.length - 1 ? SEQUENCE[i + 1] : null
}

async function prepInputs(name) {
	await call('lms.lms.trainee_payroll.prepare_weekly_inputs', { cycle_name: name })
}

async function advance(name, newStatus) {
	await call('frappe.client.get_doc', { doctype: 'Weekly Payroll Cycle', name }).then(async (doc) => {
		await call('run_doc_method', { dt: 'Weekly Payroll Cycle', dn: name, method: 'advance_status', args: { new_status: newStatus } })
	})
	cycles.reload()
}
</script>
```

- [ ] **Step 3: Build `TraineeDashboard.vue`**

This is a minimal first cut — three real counts via three separate `createResource` calls (Frappe has no multi-filter count endpoint). Task 18 replaces this whole file with a single backend summary endpoint and the full metric set from spec §9; this version is real, working software in its own right, not a stub.

```vue
<!-- frontend/src/pages/Sales/TraineeDashboard.vue -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Dashboard</h1>
		<div class="grid grid-cols-3 gap-4 mb-6">
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ inTraining.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">In Training</div>
			</div>
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ cleared.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">Training Cleared</div>
			</div>
			<div class="border rounded p-4">
				<div class="text-2xl font-semibold">{{ exited.data ?? '—' }}</div>
				<div class="text-sm text-gray-500">Exited/Churned</div>
			</div>
		</div>
		<Button @click="downloadExport">Export Active Trainee Report</Button>
	</div>
</template>

<script setup>
import { createResource, call, Button } from 'frappe-ui'

const inTraining = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'In Training' } },
	auto: true,
})
const cleared = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'Training Cleared' } },
	auto: true,
})
const exited = createResource({
	url: 'frappe.client.get_count',
	params: { doctype: 'Sales Trainee', filters: { training_status: 'Exited/Churned' } },
	auto: true,
})

async function downloadExport() {
	const encoded = await call('lms.lms.trainee_reports.export_active_trainees_csv')
	const link = document.createElement('a')
	link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
	link.download = 'active-trainees.xlsx'
	link.click()
}
</script>
```

- [ ] **Step 4: Add nav entries**

```javascript
// frontend/src/utils/index.js
{
	label: 'Payroll cycles',
	icon: 'Wallet',
	to: 'WeeklyPayrollCycle',
	activeFor: ['WeeklyPayrollCycle'],
	condition: () => {
		const roles = userResource?.data?.roles || []
		return !forMobile && (roles.includes('Sales Training Finance') || roles.includes('Sales Training Team'))
	},
},
{
	label: 'Trainee dashboard',
	icon: 'LayoutDashboard',
	to: 'TraineeDashboard',
	activeFor: ['TraineeDashboard'],
	condition: () => {
		const tier = userResource?.data?.access_tier
		const roles = userResource?.data?.roles || []
		return !forMobile && (['Admin', 'Super Admin'].includes(tier) || roles.includes('Sales Training Leadership'))
	},
},
```

- [ ] **Step 5: Manually verify**

Log in as `Sales Training Finance`, visit `/sales-trainees/payroll`, create a `Weekly Payroll Cycle` from the Frappe desk if none exists, click "Prepare Inputs" and confirm the child table fills (check via desk), click "Advance to Ready to Share" and confirm status changes and a repeat click now offers "Advance to Shared with Vendor". Visit `/sales-trainees/dashboard` as `Sales Training Leadership`, confirm counts render and the export downloads an `.xlsx` that opens.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Sales/WeeklyPayrollCycle.vue frontend/src/pages/Sales/TraineeDashboard.vue frontend/src/router.js frontend/src/utils/index.js
git commit -m "feat: add payroll cycle workboard and trainee dashboard"
```

---

### Task 15: Trainee status/exit change audit logging

**Why this task exists:** coverage audit against the source doc (2026-09-24) found that Task 3 built the audit-log doctype and Task 4 wired it into attendance corrections, but nothing wires it into `Sales Trainee` itself. The doc's Audit History requirement (§10) explicitly covers "trainee status changes and exits," not just attendance.

**Files:**
- Modify: `backend/lms/lms/doctype/sales_trainee/sales_trainee.py`
- Modify: `backend/lms/lms/doctype/sales_trainee/test_sales_trainee.py`

**Interfaces:**
- Consumes: `write_audit_log` (Task 3).
- Produces: whitelisted doc method `update_training_status(new_status, reason, exit_status=None, exit_date=None, exit_reason=None)` — this is what Task 18's frontend must call instead of a raw field save. A direct desk edit (bypassing this method) is still logged, with a fallback reason, via `on_update()` — the audit trail is never silently skipped, only ever missing a real reason when someone edits outside the intended flow.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/doctype/sales_trainee/test_sales_trainee.py
# Add these test methods to the existing TestSalesTrainee class:

	def test_update_training_status_logs_real_reason(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Status Change Target",
				"personal_email": f"status-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.update_training_status("Training Cleared", reason="Cleared final viva on Day 21")
		trainee.reload()
		self.assertEqual(trainee.training_status, "Training Cleared")
		logs = frappe.get_all(
			"Sales Trainee Audit Log", filters={"trainee": trainee.name, "field_changed": "training_status"}
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(
			frappe.db.get_value("Sales Trainee Audit Log", logs[0].name, "reason"),
			"Cleared final viva on Day 21",
		)

	def test_update_training_status_requires_reason(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "No Reason Target",
				"personal_email": f"noreason-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.MandatoryError):
			trainee.update_training_status("Resigned", reason="")

	def test_exit_change_logged_separately_from_status(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exit Target",
				"personal_email": f"exit-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.update_training_status(
			"Resigned",
			reason="Resigned on Day 5, cited relocation",
			exit_status="Resigned",
			exit_date="2026-10-10",
			exit_reason="Relocation",
		)
		trainee.reload()
		self.assertEqual(trainee.exit_date, frappe.utils.getdate("2026-10-10"))
		field_names = set(
			frappe.get_all("Sales Trainee Audit Log", filters={"trainee": trainee.name}, pluck="field_changed")
		)
		self.assertIn("training_status", field_names)
		self.assertIn("exit_status", field_names)
		self.assertIn("exit_date", field_names)

	def test_direct_desk_edit_still_logged_with_fallback_reason(self):
		# Review Focus: a plain frappe.get_doc(...).save() from the Frappe desk
		# (not through update_training_status) must still leave an audit trail,
		# even though there is no reason field on that path.
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Desk Edit Target",
				"personal_email": f"desk-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)
		trainee.training_status = "Absconded"
		trainee.save(ignore_permissions=True)
		logs = frappe.get_all(
			"Sales Trainee Audit Log",
			filters={"trainee": trainee.name, "field_changed": "training_status"},
			fields=["reason"],
		)
		self.assertEqual(len(logs), 1)
		self.assertIn("direct edit", logs[0].reason.lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee.test_sales_trainee -v`
Expected: FAIL — `update_training_status` does not exist, and no `on_update` hook logs the direct-edit case.

- [ ] **Step 3: Implement the method and the fallback hook**

```python
# backend/lms/lms/doctype/sales_trainee/sales_trainee.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.doctype.sales_trainee_audit_log.sales_trainee_audit_log import write_audit_log

AUDITED_FIELDS = ("training_status", "exit_status", "exit_date", "exit_reason")


class SalesTrainee(Document):
	def on_update(self):
		if self.flags.get("status_change_reason_handled"):
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		for field in AUDITED_FIELDS:
			old_value, new_value = previous.get(field), self.get(field)
			if old_value != new_value:
				write_audit_log(
					trainee=self.name,
					field_changed=field,
					old_value=old_value,
					new_value=new_value,
					reason="No reason provided (direct edit)",
				)

	@frappe.whitelist()
	def update_training_status(self, new_status, reason, exit_status=None, exit_date=None, exit_reason=None):
		"""The intended path for changing training_status/exit fields — always
		captures a real reason. A raw doc.save() from the desk still gets logged
		by on_update() above, just with a fallback reason instead of this one."""
		if not (reason or "").strip():
			frappe.throw(_("A reason is required to change training status."), frappe.MandatoryError)

		changes = [("training_status", self.training_status, new_status)]
		self.training_status = new_status
		if exit_status is not None and exit_status != self.exit_status:
			changes.append(("exit_status", self.exit_status, exit_status))
			self.exit_status = exit_status
		if exit_date is not None and str(exit_date) != str(self.exit_date or ""):
			changes.append(("exit_date", self.exit_date, exit_date))
			self.exit_date = exit_date
		if exit_reason is not None and exit_reason != self.exit_reason:
			changes.append(("exit_reason", self.exit_reason, exit_reason))
			self.exit_reason = exit_reason

		self.flags.status_change_reason_handled = True
		self.save(ignore_permissions=True)

		for field, old_value, new_value in changes:
			if old_value != new_value:
				write_audit_log(
					trainee=self.name, field_changed=field, old_value=old_value, new_value=new_value, reason=reason
				)
		return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.doctype.sales_trainee.test_sales_trainee -v`
Expected: PASS (7 tests total)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/doctype/sales_trainee/
git commit -m "feat: audit-log trainee status/exit changes, with a fallback for direct desk edits"
```

---

### Task 16: Cohort stats + missing-attendance report

**Why this task exists:** coverage audit found spec §3 promises cohort counts "computed on read" and the doc's V1 scope §3 explicitly lists "Identify missing attendance" — neither had a task.

**Files:**
- Create: `backend/lms/lms/trainee_cohort_stats.py`
- Create: `backend/lms/lms/test_trainee_cohort_stats.py`

**Interfaces:**
- Consumes: `Sales Trainee`, `Sales Trainee Attendance` (Tasks 2, 4).
- Produces: `@frappe.whitelist() def get_cohort_stats(cohort)` and `@frappe.whitelist() def list_missing_attendance(attendance_date, cohort=None)`. Used by Task 12's cohort screen and Task 18's dashboard.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_cohort_stats.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark
from lms.lms.trainee_cohort_stats import get_cohort_stats, list_missing_attendance


class TestTraineeCohortStats(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.cohort = frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"Stats-Cohort-{frappe.generate_hash(length=6)}", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		self.active = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Active",
				"personal_email": f"stats-active-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"cohort": self.cohort.name,
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		self.exited = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Exited",
				"personal_email": f"stats-exited-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"cohort": self.cohort.name,
				"training_status": "Resigned",
			}
		).insert(ignore_permissions=True)

	def test_get_cohort_stats_counts_by_status(self):
		stats = get_cohort_stats(self.cohort.name)
		self.assertEqual(stats["total"], 2)
		self.assertEqual(stats["active"], 1)
		self.assertEqual(stats["exits"], 1)

	def test_list_missing_attendance_flags_unmarked_active_trainee(self):
		mark(self.exited.name, "2026-10-08", "Present")  # exited trainee not in scope anyway
		missing = list_missing_attendance("2026-10-08", cohort=self.cohort.name)
		self.assertIn(self.active.name, missing)

	def test_list_missing_attendance_excludes_marked_trainee(self):
		mark(self.active.name, "2026-10-09", "Present")
		missing = list_missing_attendance("2026-10-09", cohort=self.cohort.name)
		self.assertNotIn(self.active.name, missing)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_cohort_stats -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

```python
# backend/lms/lms/trainee_cohort_stats.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe

EXIT_STATUSES = ("Resigned", "Absconded", "Exited/Churned")


@frappe.whitelist()
def get_cohort_stats(cohort):
	rows = frappe.get_all("Sales Trainee", filters={"cohort": cohort}, fields=["training_status"])
	total = len(rows)
	exits = sum(1 for r in rows if r.training_status in EXIT_STATUSES)
	active = sum(1 for r in rows if r.training_status == "In Training")
	cleared = sum(1 for r in rows if r.training_status == "Training Cleared")
	not_cleared = sum(1 for r in rows if r.training_status == "Training Not Cleared")
	return {"total": total, "active": active, "exits": exits, "cleared": cleared, "not_cleared": not_cleared}


@frappe.whitelist()
def list_missing_attendance(attendance_date, cohort=None):
	"""Names of In Training trainees with no Sales Trainee Attendance row for the date."""
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	active_trainees = frappe.get_all("Sales Trainee", filters=filters, pluck="name")
	if not active_trainees:
		return []
	marked = set(
		frappe.get_all(
			"Sales Trainee Attendance",
			filters={"trainee": ["in", active_trainees], "attendance_date": attendance_date},
			pluck="trainee",
		)
	)
	return [name for name in active_trainees if name not in marked]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_cohort_stats -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/trainee_cohort_stats.py backend/lms/lms/test_trainee_cohort_stats.py
git commit -m "feat: add cohort stats and missing-attendance lookup"
```

---

### Task 17: Remaining report exports (spec §9 / doc §9)

**Why this task exists:** coverage audit found the doc lists 7 required exports; Task 10 built only the Active Trainee Report. This task adds the other 6 and factors out the shared XLSX-building code Task 10 duplicated inline.

**Files:**
- Modify: `backend/lms/lms/trainee_reports.py`
- Modify: `backend/lms/lms/test_trainee_reports.py`

**Interfaces:**
- Consumes: `Sales Trainee`, `Sales Trainee Attendance`, `Weekly Payroll Cycle`/`Weekly Payroll Input` (Tasks 2, 4, 5).
- Produces: `export_weekly_attendance_payroll_report(week_start, week_end)`, `export_vendor_payroll_input(cycle_name)`, `export_exit_churn_report(month=None)`, `export_training_outcome_report(cohort=None)`, `export_location_cohort_report()`, `export_finance_reconciliation_report(cycle_name)` — all `@frappe.whitelist()`, all return base64 XLSX like `export_active_trainees_csv`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/lms/lms/test_trainee_reports.py
# Add these test methods to the existing TestTraineeReports class, and add these
# imports at the top: `from lms.lms.trainee_reports import (export_active_trainees_csv,
# export_weekly_attendance_payroll_report, export_vendor_payroll_input,
# export_exit_churn_report, export_training_outcome_report,
# export_location_cohort_report, export_finance_reconciliation_report)`

	def _open_workbook(self, encoded):
		return openpyxl.load_workbook(io.BytesIO(base64.b64decode(encoded)))

	def test_export_exit_churn_report_includes_only_exited(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Churned",
				"personal_email": f"churn-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "Absconded",
				"exit_date": "2026-10-09",
				"exit_reason": "Did not return after weekend",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Still Training",
				"personal_email": f"active-churn-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		workbook = self._open_workbook(export_exit_churn_report())
		names = {row[0].value for row in workbook.active.iter_rows(min_row=2)}
		self.assertIn("Churned", names)
		self.assertNotIn("Still Training", names)

	def test_export_training_outcome_report_groups_by_status(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Cleared One",
				"personal_email": f"outcome-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"training_status": "Training Cleared",
			}
		).insert(ignore_permissions=True)
		workbook = self._open_workbook(export_training_outcome_report())
		statuses = {row[1].value for row in workbook.active.iter_rows(min_row=2)}
		self.assertIn("Training Cleared", statuses)

	def test_export_vendor_payroll_input_lists_cycle_rows(self):
		trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Vendor Row",
				"personal_email": f"vendor-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"salary": 20000,
			}
		).insert(ignore_permissions=True)
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"payroll_inputs": [{"trainee": trainee.name, "salary": 20000, "working_days": 6, "payable_days": 5}],
			}
		).insert(ignore_permissions=True)
		workbook = self._open_workbook(export_vendor_payroll_input(cycle.name))
		rows = list(workbook.active.iter_rows(min_row=2, values_only=True))
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0][0], trainee.name)

	def test_export_finance_reconciliation_report_shows_captured_vs_invoiced(self):
		cycle = frappe.get_doc(
			{
				"doctype": "Weekly Payroll Cycle",
				"week_start": "2026-10-06",
				"week_end": "2026-10-12",
				"vendor_invoice_amount": 95000,
			}
		).insert(ignore_permissions=True)
		workbook = self._open_workbook(export_finance_reconciliation_report(cycle.name))
		row = next(workbook.active.iter_rows(min_row=2, values_only=True))
		self.assertEqual(row[-1], 95000)

	def test_export_location_cohort_report_lists_every_cohort(self):
		frappe.get_doc(
			{"doctype": "Sales Trainee Cohort", "cohort_name": f"Loc-{frappe.generate_hash(length=6)}", "location": "Chennai", "start_date": "2026-10-06"}
		).insert(ignore_permissions=True)
		workbook = self._open_workbook(export_location_cohort_report())
		locations = {row[1].value for row in workbook.active.iter_rows(min_row=2)}
		self.assertIn("Chennai", locations)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_reports -v`
Expected: FAIL — the new export functions don't exist yet.

- [ ] **Step 3: Refactor the shared XLSX builder and add the 6 exports**

```python
# backend/lms/lms/trainee_reports.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import base64
import io

import frappe
import openpyxl


def _to_xlsx(sheet_title, headers, rows):
	workbook = openpyxl.Workbook()
	sheet = workbook.active
	sheet.title = sheet_title
	sheet.append(headers)
	for row in rows:
		sheet.append(row)
	buffer = io.BytesIO()
	workbook.save(buffer)
	return base64.b64encode(buffer.getvalue()).decode("utf-8")


@frappe.whitelist()
def export_active_trainees_csv(cohort=None, location=None):
	"""Active Trainee Report (spec §9)."""
	filters = {"training_status": "In Training"}
	if cohort:
		filters["cohort"] = cohort
	if location:
		filters["location"] = location
	rows = frappe.get_all(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "personal_email", "location", "cohort", "date_of_joining", "employee_dummy_vendor_code"],
		order_by="date_of_joining asc",
	)
	return _to_xlsx(
		"Active Trainees",
		["Trainee Name", "Personal Email", "Location", "Cohort", "Date of Joining", "Employee/Dummy/Vendor Code"],
		[[r.trainee_name, r.personal_email, r.location, r.cohort, str(r.date_of_joining or ""), r.employee_dummy_vendor_code] for r in rows],
	)


@frappe.whitelist()
def export_weekly_attendance_payroll_report(week_start, week_end):
	rows = frappe.get_all(
		"Sales Trainee Attendance",
		filters={"attendance_date": ["between", [week_start, week_end]]},
		fields=["trainee", "attendance_date", "status", "source"],
		order_by="attendance_date asc",
	)
	return _to_xlsx(
		"Weekly Attendance",
		["Trainee", "Date", "Status", "Source"],
		[[r.trainee, str(r.attendance_date), r.status, r.source] for r in rows],
	)


@frappe.whitelist()
def export_vendor_payroll_input(cycle_name):
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	return _to_xlsx(
		"Vendor Payroll Input",
		["Trainee", "Salary", "Working Days", "Payable Days", "Adjustment Note"],
		[[r.trainee, r.salary, r.working_days, r.payable_days, r.joining_or_exit_adjustment_note] for r in cycle.payroll_inputs],
	)


@frappe.whitelist()
def export_exit_churn_report(month=None):
	filters = {"training_status": ["in", ["Resigned", "Absconded", "Exited/Churned"]]}
	rows = frappe.get_all(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "training_status", "exit_date", "exit_reason", "cohort"],
		order_by="exit_date desc",
	)
	if month:
		rows = [r for r in rows if r.exit_date and str(r.exit_date).startswith(month)]
	return _to_xlsx(
		"Exit and Churn",
		["Trainee Name", "Exit Status", "Exit Date", "Exit Reason", "Cohort"],
		[[r.trainee_name, r.training_status, str(r.exit_date or ""), r.exit_reason, r.cohort] for r in rows],
	)


@frappe.whitelist()
def export_training_outcome_report(cohort=None):
	filters = {}
	if cohort:
		filters["cohort"] = cohort
	rows = frappe.get_all(
		"Sales Trainee",
		filters=filters,
		fields=["trainee_name", "training_status", "location", "cohort"],
		order_by="cohort asc",
	)
	return _to_xlsx(
		"Training Outcomes",
		["Trainee Name", "Training Status", "Location", "Cohort"],
		[[r.trainee_name, r.training_status, r.location, r.cohort] for r in rows],
	)


@frappe.whitelist()
def export_location_cohort_report():
	from lms.lms.trainee_cohort_stats import get_cohort_stats

	cohorts = frappe.get_all("Sales Trainee Cohort", fields=["name", "location", "start_date"])
	rows = []
	for c in cohorts:
		stats = get_cohort_stats(c.name)
		rows.append([c.name, c.location, str(c.start_date or ""), stats["total"], stats["active"], stats["exits"]])
	return _to_xlsx(
		"Location and Cohort",
		["Cohort", "Location", "Start Date", "Total", "Active", "Exits"],
		rows,
	)


@frappe.whitelist()
def export_finance_reconciliation_report(cycle_name):
	cycle = frappe.get_doc("Weekly Payroll Cycle", cycle_name)
	captured_total = sum((row.salary or 0) * (row.payable_days or 0) / max(row.working_days or 1, 1) for row in cycle.payroll_inputs)
	return _to_xlsx(
		"Finance Reconciliation",
		["Cycle", "Week Start", "Week End", "Status", "Captured Estimate", "Vendor Invoice Amount"],
		[[cycle.name, str(cycle.week_start), str(cycle.week_end), cycle.status, round(captured_total, 2), cycle.vendor_invoice_amount]],
	)
```

Note: `export_finance_reconciliation_report`'s "Captured Estimate" column is a display-only cross-check for Finance to eyeball against the vendor's number — it is **not** a pro-rata calculation the system relies on anywhere else (spec §2 still holds: capture only, no computed payout).

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_reports -v`
Expected: PASS (6 tests total)

- [ ] **Step 5: Commit**

```bash
git add backend/lms/lms/trainee_reports.py backend/lms/lms/test_trainee_reports.py
git commit -m "feat: add remaining 6 report exports from spec §9"
```

---

### Task 18: Complete dashboard metrics + filters

**Why this task exists:** coverage audit found Task 14's dashboard only wired 3 of the ~10 metrics the doc lists (§8), via a placeholder wiring note. This task replaces that stub with a single backend summary endpoint and the full metric set with month/location/cohort filters.

**Files:**
- Create: `backend/lms/lms/trainee_dashboard.py`
- Create: `backend/lms/lms/test_trainee_dashboard.py`
- Modify: `frontend/src/pages/Sales/TraineeDashboard.vue`

**Interfaces:**
- Consumes: `Sales Trainee`, `Weekly Payroll Cycle` (Tasks 2, 5), `update_training_status` (Task 15).
- Produces: `@frappe.whitelist() def get_dashboard_summary(month=None, location=None, cohort=None)` — replaces the three ad-hoc `createResource` calls Task 14 left as a placeholder.

- [ ] **Step 1: Write the failing test**

```python
# backend/lms/lms/test_trainee_dashboard.py
import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_dashboard import get_dashboard_summary


class TestTraineeDashboard(UnitTestCase):
	def setUp(self):
		super().setUp()
		for status in ("In Training", "Training Cleared", "Resigned", "Absconded"):
			frappe.get_doc(
				{
					"doctype": "Sales Trainee",
					"trainee_name": f"Dash {status}",
					"personal_email": f"dash-{status.lower().replace(' ', '')}-{frappe.generate_hash(length=6)}@example.com",
					"date_of_joining": "2026-10-06",
					"location": "Pune",
					"training_status": status,
					"salary": 20000,
				}
			).insert(ignore_permissions=True)

	def test_summary_counts_every_status(self):
		summary = get_dashboard_summary()
		self.assertEqual(summary["in_training"], 1)
		self.assertEqual(summary["training_cleared"], 1)
		self.assertEqual(summary["resigned"], 1)
		self.assertEqual(summary["absconded"], 1)
		self.assertEqual(summary["total"], 4)

	def test_summary_filters_by_location(self):
		frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Elsewhere",
				"personal_email": f"dash-elsewhere-{frappe.generate_hash(length=6)}@example.com",
				"date_of_joining": "2026-10-06",
				"location": "Nagpur",
				"training_status": "In Training",
			}
		).insert(ignore_permissions=True)
		summary = get_dashboard_summary(location="Pune")
		self.assertEqual(summary["total"], 4)

	def test_summary_includes_payroll_eligible_count(self):
		summary = get_dashboard_summary()
		# Training Cleared trainees are payroll-eligible per spec §5/doc §5
		self.assertEqual(summary["payroll_eligible"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_dashboard -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

```python
# backend/lms/lms/trainee_dashboard.py
# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe

STATUS_KEYS = {
	"In Training": "in_training",
	"Resigned": "resigned",
	"Absconded": "absconded",
	"Exited/Churned": "exited_churned",
	"Training Cleared": "training_cleared",
	"Training Not Cleared": "training_not_cleared",
}


@frappe.whitelist()
def get_dashboard_summary(month=None, location=None, cohort=None):
	filters = {}
	if location:
		filters["location"] = location
	if cohort:
		filters["cohort"] = cohort
	if month:
		filters["date_of_joining"] = ["like", f"{month}%"]

	rows = frappe.get_all("Sales Trainee", filters=filters, fields=["training_status"])
	summary = dict.fromkeys(STATUS_KEYS.values(), 0)
	for row in rows:
		key = STATUS_KEYS.get(row.training_status)
		if key:
			summary[key] += 1
	summary["total"] = len(rows)
	summary["payroll_eligible"] = summary["training_cleared"]

	open_cycles = frappe.get_all("Weekly Payroll Cycle", filters={"status": ["!=", "Closed"]}, fields=["status"])
	summary["open_payroll_cycles"] = len(open_cycles)
	return summary
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site frappe.local run-tests --app lms --module lms.lms.test_trainee_dashboard -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Replace Task 14's placeholder counts wiring in the frontend**

```vue
<!-- frontend/src/pages/Sales/TraineeDashboard.vue -->
<!-- Replace the entire <script setup> block from Task 14 with: -->
<script setup>
import { ref, watch } from 'vue'
import { createResource, call, Button } from 'frappe-ui'

const month = ref('')
const location = ref('')
const cohort = ref('')

const summary = createResource({
	url: 'lms.lms.trainee_dashboard.get_dashboard_summary',
	params: { month: month.value, location: location.value, cohort: cohort.value },
	auto: true,
})

watch([month, location, cohort], () => {
	summary.update({ params: { month: month.value, location: location.value, cohort: cohort.value } })
	summary.reload()
})

async function downloadExport() {
	const encoded = await call('lms.lms.trainee_reports.export_active_trainees_csv')
	const link = document.createElement('a')
	link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${encoded}`
	link.download = 'active-trainees.xlsx'
	link.click()
}
</script>
```

```vue
<!-- Replace the <template> block from Task 14 with: -->
<template>
	<div class="p-6 max-w-4xl mx-auto">
		<h1 class="text-xl font-semibold mb-4">Trainee Dashboard</h1>
		<div class="flex gap-2 mb-4">
			<input v-model="month" type="month" class="border rounded px-2 py-1" placeholder="Month" />
			<input v-model="location" type="text" class="border rounded px-2 py-1" placeholder="Location" />
			<input v-model="cohort" type="text" class="border rounded px-2 py-1" placeholder="Cohort" />
		</div>
		<div class="grid grid-cols-4 gap-4 mb-6">
			<div class="border rounded p-4" v-for="(label, key) in {
				in_training: 'In Training', training_cleared: 'Training Cleared',
				training_not_cleared: 'Training Not Cleared', resigned: 'Resigned',
				absconded: 'Absconded', exited_churned: 'Exited/Churned',
				payroll_eligible: 'Payroll Eligible', open_payroll_cycles: 'Open Payroll Cycles',
			}" :key="key">
				<div class="text-2xl font-semibold">{{ summary.data?.[key] ?? '—' }}</div>
				<div class="text-sm text-gray-500">{{ label }}</div>
			</div>
		</div>
		<Button @click="downloadExport">Export Active Trainee Report</Button>
	</div>
</template>
```

- [ ] **Step 6: Manually verify**

Visit `/sales-trainees/dashboard`, confirm all 8 tiles render real numbers, type a location into the filter and confirm the tiles update.

- [ ] **Step 7: Commit**

```bash
git add backend/lms/lms/trainee_dashboard.py backend/lms/lms/test_trainee_dashboard.py frontend/src/pages/Sales/TraineeDashboard.vue
git commit -m "feat: complete dashboard with full metric set and month/location/cohort filters"
```

---

## Full suite check (run once, after Task 18)

```bash
bench --site frappe.local run-tests --app lms --coverage
```

Expected: PASS across all new modules; no regressions in existing suites.
