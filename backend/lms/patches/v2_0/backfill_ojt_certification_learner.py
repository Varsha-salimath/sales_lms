import frappe


def execute():
	if not frappe.db.exists("DocType", "Sales OJT Certification Metric"):
		return
	if not frappe.db.has_column("Sales OJT Certification Metric", "learner"):
		return
	rows = frappe.get_all(
		"Sales OJT Certification Metric",
		fields=["name", "email", "learner"],
	)
	for row in rows:
		if row.learner or not row.email:
			continue
		user = frappe.db.get_value("User", {"email": row.email}, "name")
		if not user and frappe.db.exists("User", row.email):
			user = row.email
		if user:
			frappe.db.set_value(
				"Sales OJT Certification Metric",
				row.name,
				"learner",
				user,
				update_modified=False,
			)
