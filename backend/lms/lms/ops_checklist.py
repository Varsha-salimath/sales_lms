# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


def _ensure_logged_in():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


@frappe.whitelist()
def get_ops_checklist_tour_state():
	_ensure_logged_in()
	skipped_on = frappe.db.get_value("Ops Checklist Tour State", frappe.session.user, "skipped_on")
	return {"skipped": bool(skipped_on), "skipped_on": skipped_on}


@frappe.whitelist()
def skip_ops_checklist_tour():
	_ensure_logged_in()
	if frappe.db.exists("Ops Checklist Tour State", frappe.session.user):
		frappe.db.set_value("Ops Checklist Tour State", frappe.session.user, "skipped_on", now_datetime())
	else:
		frappe.get_doc(
			{"doctype": "Ops Checklist Tour State", "user": frappe.session.user, "skipped_on": now_datetime()}
		).insert(ignore_permissions=True)
	return {"skipped": True}
