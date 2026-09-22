# Copyright (c) 2026, Infinity Learn and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class LMSIdentityChange(Document):
	"""Audit trail: a learner's login email or employee code changed. Written only by lms.lms.identity."""
