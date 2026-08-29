# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Bootstrap Desk Email Account from required SMTP_* environment variables."""

from __future__ import annotations

import os

import frappe
from frappe import _


def ensure_outgoing_email_from_env() -> dict:
	"""
	Create or update the default outgoing Email Account from SMTP_* env vars.
	SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and DEFAULT_SENDER are required.
	Safe to call repeatedly (idempotent on email_id / default_outgoing).
	"""
	host = (os.environ.get("SMTP_HOST") or "").strip()
	user = (os.environ.get("SMTP_USER") or "").strip()
	password = os.environ.get("SMTP_PASSWORD") or ""
	sender = (os.environ.get("DEFAULT_SENDER") or "").strip()

	missing = [
		name
		for name, value in (
			("SMTP_HOST", host),
			("SMTP_USER", user),
			("SMTP_PASSWORD", password),
			("DEFAULT_SENDER", sender),
		)
		if not value
	]
	if missing:
		frappe.throw(_("Required SMTP settings missing: {0}").format(", ".join(missing)))

	port = int(os.environ.get("SMTP_PORT") or 587)
	use_tls = str(os.environ.get("SMTP_TLS") or "1").lower() in {"1", "true", "yes"}
	use_ssl = str(os.environ.get("SMTP_SSL") or "0").lower() in {"1", "true", "yes"}
	sender_name = (os.environ.get("DEFAULT_SENDER_NAME") or "Sales LMS").strip()

	existing = frappe.db.get_value(
		"Email Account",
		{"email_id": sender, "enable_outgoing": 1},
		"name",
	) or frappe.db.get_value("Email Account", {"default_outgoing": 1}, "name")

	if existing:
		doc = frappe.get_doc("Email Account", existing)
	else:
		doc = frappe.new_doc("Email Account")
		doc.email_account_name = "Sales LMS Outgoing"

	doc.email_id = sender
	doc.email_account_name = doc.email_account_name or "Sales LMS Outgoing"
	doc.enable_outgoing = 1
	doc.default_outgoing = 1
	doc.smtp_server = host
	doc.smtp_port = port
	# Field names vary slightly across Frappe versions — set safely
	if hasattr(doc, "use_tls"):
		doc.use_tls = 1 if use_tls and not use_ssl else 0
	if hasattr(doc, "use_ssl"):
		doc.use_ssl = 1 if use_ssl else 0
	elif hasattr(doc, "use_ssl_for_outgoing"):
		doc.use_ssl_for_outgoing = 1 if use_ssl else 0
	# AWS SES (and similar) use an IAM SMTP user that differs from the From address
	if user.lower() != sender.lower():
		doc.login_id_is_different = 1
		doc.login_id = user
	else:
		doc.login_id_is_different = 0
		doc.login_id = user
	if hasattr(doc, "awaiting_password"):
		doc.awaiting_password = 0
	doc.password = password
	if hasattr(doc, "always_use_account_email_id_as_sender"):
		doc.always_use_account_email_id_as_sender = 1
	if hasattr(doc, "always_use_account_name_as_sender_name"):
		doc.always_use_account_name_as_sender_name = 1
	if hasattr(doc, "send_unsubscribe_message"):
		doc.send_unsubscribe_message = 0
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	# Email Account.validate() opens a live SMTP session unless in_patch / in_install / in_test.
	prev_patch = bool(getattr(frappe.local.flags, "in_patch", False))
	prev_install = bool(getattr(frappe.local.flags, "in_install", False))
	frappe.local.flags.in_patch = True
	frappe.local.flags.in_install = True
	try:
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	finally:
		frappe.local.flags.in_patch = prev_patch
		frappe.local.flags.in_install = prev_install


	return {
		"configured": 1,
		"email_account": doc.name,
		"email_id": sender,
		"smtp_server": host,
		"smtp_port": port,
		"sender_name": sender_name,
	}
