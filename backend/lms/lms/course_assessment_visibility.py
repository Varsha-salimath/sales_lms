import frappe


def get_batches_for_course(course: str) -> list[dict]:
	return frappe.db.sql(
		"""
		SELECT DISTINCT b.name, b.title
		FROM `tabLMS Batch` b
		INNER JOIN `tabBatch Course` bc ON bc.parent = b.name
		WHERE bc.course = %s
		ORDER BY b.title
		""",
		course,
		as_dict=True,
	)


def get_member_batches_for_course(member: str, course: str) -> list[str]:
	if not member or member == "Guest":
		return []

	return frappe.db.sql(
		"""
		SELECT DISTINCT be.batch
		FROM `tabLMS Batch Enrollment` be
		INNER JOIN `tabBatch Course` bc ON bc.parent = be.batch
		WHERE be.member = %s AND bc.course = %s
		""",
		(member, course),
		pluck=True,
	)


def ensure_visibility_rows(course: str) -> None:
	batches = get_batches_for_course(course)
	if not batches:
		return

	assessments = frappe.get_all(
		"LMS Assessment",
		{"parent": course, "parenttype": "LMS Course"},
		pluck="name",
	)

	for assessment_name in assessments:
		for batch in batches:
			if frappe.db.exists(
				"LMS Course Assessment Visibility",
				{"course_assessment": assessment_name, "batch": batch.name},
			):
				continue

			frappe.get_doc(
				{
					"doctype": "LMS Course Assessment Visibility",
					"course": course,
					"course_assessment": assessment_name,
					"batch": batch.name,
					"is_visible": 0,
				}
			).insert(ignore_permissions=True)


def delete_visibility_for_assessment(course_assessment: str) -> None:
	frappe.db.delete("LMS Course Assessment Visibility", {"course_assessment": course_assessment})


def delete_visibility_for_course(course: str) -> None:
	frappe.db.delete("LMS Course Assessment Visibility", {"course": course})


def get_visibility_map(course: str) -> dict:
	rows = frappe.get_all(
		"LMS Course Assessment Visibility",
		{"course": course},
		["course_assessment", "batch", "is_visible", "name"],
	)
	result = {}
	for row in rows:
		result.setdefault(row.course_assessment, {})[row.batch] = {
			"name": row.name,
			"is_visible": row.is_visible,
		}
	return result


def set_visibility(course_assessment: str, batch: str, is_visible: int | bool) -> dict:
	course = frappe.db.get_value("LMS Assessment", course_assessment, "parent")
	ensure_visibility_rows(course)
	docname = f"{course_assessment}-{batch}"

	if frappe.db.exists("LMS Course Assessment Visibility", docname):
		frappe.db.set_value(
			"LMS Course Assessment Visibility",
			docname,
			"is_visible",
			1 if is_visible else 0,
		)
	else:
		frappe.get_doc(
			{
				"doctype": "LMS Course Assessment Visibility",
				"course": course,
				"course_assessment": course_assessment,
				"batch": batch,
				"is_visible": 1 if is_visible else 0,
			}
		).insert(ignore_permissions=True)

	return {"course_assessment": course_assessment, "batch": batch, "is_visible": 1 if is_visible else 0}


def get_live_course_assessments_for_batch(batch: str) -> list[dict]:
	"""Course assessments marked live for this batch (from course editor visibility)."""
	courses = frappe.get_all("Batch Course", {"parent": batch}, pluck="course")
	if not courses:
		return []

	visibility_rows = frappe.get_all(
		"LMS Course Assessment Visibility",
		{"batch": batch, "is_visible": 1, "course": ["in", courses]},
		["course_assessment", "course"],
	)

	assessments = []
	for row in visibility_rows:
		assessment = frappe.db.get_value(
			"LMS Assessment",
			row.course_assessment,
			["name", "assessment_type", "assessment_name", "display_title"],
			as_dict=True,
		)
		if not assessment:
			continue

		source_title = frappe.db.get_value(
			assessment.assessment_type, assessment.assessment_name, "title"
		)
		assessments.append(
			{
				"name": assessment.name,
				"assessment_name": assessment.assessment_name,
				"assessment_type": assessment.assessment_type,
				"title": assessment.display_title or source_title,
				"course": row.course,
				"course_title": frappe.db.get_value("LMS Course", row.course, "title"),
				"from_course": True,
			}
		)

	return assessments
