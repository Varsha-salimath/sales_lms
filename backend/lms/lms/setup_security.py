"""Apply LMS security settings from environment (local vs prod)."""

from __future__ import annotations

import os

import frappe
from frappe.utils import cint


def _env_int(name: str, default: int) -> int:
	raw = os.environ.get(name)
	if raw is None or str(raw).strip() == "":
		return default
	return cint(raw)


def ensure_lms_security_from_env():
	"""Sync developer_mode, guest access, signup, and demo-learner flags from env."""
	dev_mode = _env_int("DEVELOPER_MODE", 0)
	allow_guest = _env_int("LMS_ALLOW_GUEST_ACCESS", 1 if dev_mode else 0)
	disable_signup = _env_int("LMS_DISABLE_SIGNUP", 0 if dev_mode else 1)
	allow_demo = _env_int("ALLOW_DEMO_LEARNER", 1 if dev_mode else 0)

	frappe.conf.developer_mode = dev_mode
	frappe.db.set_single_value("LMS Settings", "allow_guest_access", allow_guest)
	frappe.db.set_single_value("LMS Settings", "disable_signup", disable_signup)
	frappe.db.set_single_value("Website Settings", "disable_signup", disable_signup)

	from frappe.installer import update_site_config

	update_site_config("developer_mode", dev_mode)
	update_site_config("allow_demo_learner", allow_demo)

	frappe.db.commit()
	frappe.clear_cache()

	return {
		"developer_mode": dev_mode,
		"allow_guest_access": allow_guest,
		"disable_signup": disable_signup,
		"allow_demo_learner": allow_demo,
	}
