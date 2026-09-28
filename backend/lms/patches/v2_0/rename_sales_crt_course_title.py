# Copyright (c) 2026, Varsity Education and contributors

import frappe

from lms.lms.sales_crt import COURSE_SLUG, COURSE_TITLE, CRT_EXPANSION, LEGACY_COURSE_TITLE


def execute():
	if not frappe.db.exists("DocType", "LMS Course"):
		return
	if frappe.db.exists("LMS Course", COURSE_SLUG):
		current = frappe.db.get_value("LMS Course", COURSE_SLUG, "title")
		if current in (LEGACY_COURSE_TITLE, COURSE_TITLE) and current != COURSE_TITLE:
			frappe.db.set_value("LMS Course", COURSE_SLUG, "title", COURSE_TITLE, update_modified=False)
		short = frappe.db.get_value("LMS Course", COURSE_SLUG, "short_introduction") or ""
		if "Classroom Readiness Training" in short:
			frappe.db.set_value(
				"LMS Course",
				COURSE_SLUG,
				"short_introduction",
				short.replace("Classroom Readiness Training", CRT_EXPANSION),
				update_modified=False,
			)
		desc = frappe.db.get_value("LMS Course", COURSE_SLUG, "description") or ""
		if "Classroom Readiness Training" in desc:
			frappe.db.set_value(
				"LMS Course",
				COURSE_SLUG,
				"description",
				desc.replace("Classroom Readiness Training", CRT_EXPANSION),
				update_modified=False,
			)

	for row in frappe.get_all(
		"Batch Course",
		filters={"title": LEGACY_COURSE_TITLE},
		pluck="name",
	):
		frappe.db.set_value("Batch Course", row, "title", COURSE_TITLE, update_modified=False)

	for row in frappe.get_all("LMS Course", filters={"title": LEGACY_COURSE_TITLE}, pluck="name"):
		if row == COURSE_SLUG:
			continue
		frappe.db.set_value("LMS Course", row, "title", COURSE_TITLE, update_modified=False)
