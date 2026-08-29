import frappe


def execute():
	"""Unique (learner, course) for LMS Course Feedback — prevent race duplicate submits."""
	if not frappe.db.exists("DocType", "LMS Course Feedback"):
		return
	try:
		frappe.db.add_unique("LMS Course Feedback", ["learner", "course"])
	except Exception:
		# Index may already exist on some backends
		frappe.log_error(title="LMS Course Feedback unique index")
