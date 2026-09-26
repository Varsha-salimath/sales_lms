# Copyright (c) 2026, Varsity Education and contributors

import frappe

from lms.lms.doctype.lms_member.lms_member import highest_access_role, normalize_access_roles_list


def execute():
	if not frappe.db.exists("DocType", "LMS Member"):
		return
	if not frappe.db.has_column("LMS Member", "access_roles"):
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "LMS Member",
				"fieldname": "access_roles",
				"fieldtype": "JSON",
				"label": "Access Roles",
				"insert_after": "access_role",
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(doctype="LMS Member")

	for row in frappe.get_all("LMS Member", fields=["name", "access_role"]):
		current = frappe.db.get_value("LMS Member", row.name, "access_roles")
		if current:
			continue
		roles = normalize_access_roles_list([row.access_role or "User"])
		frappe.db.set_value(
			"LMS Member",
			row.name,
			{"access_roles": roles, "access_role": highest_access_role(roles)},
			update_modified=False,
		)
