import json

import frappe


def execute():
	"""Replace MariaDB-era progress LIKE filters with numeric >= for Postgres."""
	new_filter = json.dumps({"progress": [">=", 100]})
	frappe.db.sql(
		"""
		UPDATE "tabWorkspace Shortcut"
		SET stats_filter = %s
		WHERE stats_filter ILIKE %s
		   OR (label = 'Course Completed' AND link_to = 'LMS Enrollment')
		""",
		(new_filter, "%like%100%"),
	)
	# Ensure Course Completed always uses numeric compare
	frappe.db.sql(
		"""
		UPDATE "tabWorkspace Shortcut"
		SET stats_filter = %s
		WHERE label = 'Course Completed' AND link_to = 'LMS Enrollment'
		""",
		(new_filter,),
	)
