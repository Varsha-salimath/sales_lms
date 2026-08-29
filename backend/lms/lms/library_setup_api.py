"""Whitelisted API to set up Library for an instructor."""

import frappe
from frappe import _

from lms.lms.setup_library_user import setup_library_user


def _ensure_setup_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if not frappe.utils.has_common(
		["Moderator", "System Manager"],
		frappe.get_roles(),
	):
		frappe.throw(_("Only moderators can run Library user setup."), frappe.PermissionError)


@frappe.whitelist()
def configure_library_user(email: str, account_name: str | None = None, batch_name: str | None = None):
	_ensure_setup_access()
	return setup_library_user(email=email, account_name=account_name, batch_name=batch_name)
