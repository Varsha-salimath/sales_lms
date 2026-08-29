"""Manual student assignments for LMS recordings."""

import frappe
from frappe import _


STAFF_ROLES = {"Moderator", "Course Creator", "Batch Evaluator"}


def is_library_staff(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return not STAFF_ROLES.isdisjoint(frappe.get_roles(user))


def get_assigned_recording_ids(user: str) -> list[str]:
	return frappe.get_all(
		"LMS Recording Assignment",
		filters={"member": user},
		pluck="recording",
	)


def get_assignment_counts(recording_names: list[str]) -> dict[str, int]:
	counts = dict.fromkeys(recording_names, 0)
	if not recording_names:
		return counts

	for row in frappe.get_all(
		"LMS Recording Assignment",
		filters={"recording": ["in", recording_names]},
		fields=["recording"],
	):
		counts[row.recording] = counts.get(row.recording, 0) + 1
	return counts


def get_recording_assignments(recording: str) -> list[dict]:
	if not frappe.db.exists("LMS Recording", recording):
		frappe.throw(_("Recording not found."))

	return frappe.get_all(
		"LMS Recording Assignment",
		filters={"recording": recording},
		fields=["name", "member", "member_name", "assigned_by", "creation"],
		order_by="member_name asc",
	)


def set_recording_assignments(recording: str, members: list[str]) -> dict:
	if not is_library_staff():
		frappe.throw(_("You are not permitted to assign recordings."), frappe.PermissionError)

	if not frappe.db.exists("LMS Recording", recording):
		frappe.throw(_("Recording not found."))

	members = list(dict.fromkeys(m.strip().lower() for m in members if m and m.strip()))
	for member in members:
		if not frappe.db.exists("User", member):
			frappe.throw(_("User {0} not found.").format(member))

	existing = frappe.get_all(
		"LMS Recording Assignment",
		filters={"recording": recording},
		fields=["name", "member"],
	)
	existing_members = {row.member for row in existing}
	target_members = set(members)

	for row in existing:
		if row.member not in target_members:
			frappe.delete_doc("LMS Recording Assignment", row.name, ignore_permissions=True)

	for member in members:
		if member in existing_members:
			continue
		frappe.get_doc(
			{
				"doctype": "LMS Recording Assignment",
				"recording": recording,
				"member": member,
				"assigned_by": frappe.session.user,
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()
	return {
		"recording": recording,
		"assigned_count": len(members),
		"members": members,
	}
