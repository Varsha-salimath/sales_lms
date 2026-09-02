import json

import frappe


def execute():
	"""Replace MariaDB-era progress LIKE filters with numeric >= for Postgres/MySQL."""
	new_filter = json.dumps({"progress": [">=", 100]})
	if frappe.conf.db_type == "postgres":
		frappe.db.sql(
			"""
			UPDATE "tabWorkspace Shortcut"
			SET stats_filter = %s
			WHERE stats_filter ILIKE %s
			   OR (label = 'Course Completed' AND link_to = 'LMS Enrollment')
			""",
			(new_filter, "%like%100%"),
		)
	else:
		frappe.db.sql(
			"""
			UPDATE `tabWorkspace Shortcut`
			SET stats_filter = %s
			WHERE stats_filter LIKE %s
			   OR (label = 'Course Completed' AND link_to = 'LMS Enrollment')
			""",
			(new_filter, "%like%100%"),
		)
	frappe.db.sql(
		"""
		UPDATE {table}
		SET stats_filter = %s
		WHERE label = 'Course Completed' AND link_to = 'LMS Enrollment'
		""".format(
			table='`tabWorkspace Shortcut`'
			if frappe.conf.db_type != "postgres"
			else '"tabWorkspace Shortcut"'
		),
		(new_filter,),
	)
