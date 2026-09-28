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
