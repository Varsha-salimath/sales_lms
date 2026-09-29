# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime


def _ensure_logged_in():
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)


@frappe.whitelist()
def get_app_welcome_tour_state():
	_ensure_logged_in()
	skipped_on = frappe.db.get_value("App Welcome Tour State", frappe.session.user, "skipped_on")
	return {"skipped": bool(skipped_on), "skipped_on": skipped_on}


@frappe.whitelist()
def skip_app_welcome_tour():
	_ensure_logged_in()
	if frappe.db.exists("App Welcome Tour State", frappe.session.user):
		frappe.db.set_value("App Welcome Tour State", frappe.session.user, "skipped_on", now_datetime())
	else:
		frappe.get_doc(
			{"doctype": "App Welcome Tour State", "user": frappe.session.user, "skipped_on": now_datetime()}
		).insert(ignore_permissions=True)
	return {"skipped": True}
