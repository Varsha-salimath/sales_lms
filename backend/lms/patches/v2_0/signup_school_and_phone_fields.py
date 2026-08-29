import frappe


def execute():
	"""Ensure User.college is labeled School Name and visible in filters for admins."""
	if frappe.db.exists("Custom Field", "User-verify_terms"):
		frappe.db.set_value(
			"Custom Field",
			"User-verify_terms",
			{"label": "Terms & Conditions Accepted"},
			update_modified=False,
		)

	if frappe.db.exists("Custom Field", "User-college"):
		frappe.db.set_value(
			"Custom Field",
			"User-college",
			{
				"label": "School Name",
				"in_standard_filter": 1,
			},
			update_modified=False,
		)

	if not frappe.db.exists("Custom Field", "User-school_name"):
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "User",
				"fieldname": "school_name",
				"label": "School Name",
				"fieldtype": "Data",
				"insert_after": "college",
				"in_standard_filter": 1,
				"translatable": 1,
			}
		).insert(ignore_permissions=True)

	# Keep branch after school_name when present
	if frappe.db.exists("Custom Field", "User-branch"):
		frappe.db.set_value(
			"Custom Field",
			"User-branch",
			{"insert_after": "school_name"},
			update_modified=False,
		)

	frappe.clear_cache(doctype="User")
