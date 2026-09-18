import frappe


def execute():
	from lms.lms.ojt_certification import seed_ojt_certification_metrics_if_empty

	if not frappe.db.exists("DocType", "Sales OJT Certification Metric"):
		return
	seed_ojt_certification_metrics_if_empty()
