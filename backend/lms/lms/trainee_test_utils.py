# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""Shared fixtures for the Sales Trainee test modules (not itself a test module)."""

import frappe


def make_user(prefix, *roles):
	"""A fresh, per-run-unique User holding exactly `roles`."""
	email = f"{prefix}-{frappe.generate_hash(length=8)}@example.com"
	user = frappe.get_doc({"doctype": "User", "email": email, "first_name": prefix}).insert(
		ignore_permissions=True
	)
	if roles:
		user.add_roles(*roles)
	return email


def make_trainee(label, **fields):
	doc = {
		"doctype": "Sales Trainee",
		"trainee_name": label,
		"personal_email": f"{label.lower().replace(' ', '-')}-{frappe.generate_hash(length=8)}@example.com",
		"date_of_joining": "2026-10-06",
	}
	doc.update(fields)
	return frappe.get_doc(doc).insert(ignore_permissions=True)


def run_as(testcase, user):
	frappe.set_user(user)
	testcase.addCleanup(frappe.set_user, "Administrator")


def call_doc_method(doctype, name, method, **args):
	"""Invoke a whitelisted Document method the way the frontend does."""
	from frappe.handler import run_doc_method

	frappe.response.setdefault("docs", [])
	# run_doc_method validates the HTTP verb, so simulate the frontend's POST.
	had_request = hasattr(frappe.local, "request")
	previous = frappe.local.request if had_request else None
	frappe.local.request = frappe._dict(method="POST")
	try:
		return run_doc_method(method=method, dt=doctype, dn=name, args=frappe.as_json(args))
	finally:
		if had_request:
			frappe.local.request = previous
		else:
			del frappe.local.request
