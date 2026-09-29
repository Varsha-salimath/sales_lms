# Copyright (c) 2026, Infinity Learn and contributors
# For license information, please see license.txt

"""Request limits that count people, not offices.

Frappe's own rate limiter counts requests per IP address. On a company portal that is the wrong
unit: everyone in an office shares one public IP, so the more colleagues are working, the sooner
each of them is told to try again later — while a single person at home gets the whole budget.

Signed-in requests are therefore counted against the account, and only anonymous ones fall back to
the IP (where there is no account to count, and where scraping actually needs holding back).
"""

from __future__ import annotations

from functools import wraps

import frappe
from frappe import _

# An internal tool: the whole office sits behind one IP, so both limits are set far above real use.
# They exist only to stop a runaway loop or a script, not to ration people.
SIGNED_IN_LIMIT = 10000  # per hour, per person
GUEST_LIMIT = 10000  # per hour, per IP (everyone in an office shares one before they log in)


def portal_rate_limit(limit: int = SIGNED_IN_LIMIT, guest_limit: int = GUEST_LIMIT, seconds: int = 3600):
	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			if not frappe.request:
				return fn(*args, **kwargs)  # background jobs and bench commands aren't traffic
			user = getattr(frappe.session, "user", None) or "Guest"
			if user == "Guest":
				identity, allowed = f"ip:{frappe.local.request_ip}", guest_limit
			else:
				identity, allowed = f"user:{user}", limit
			key = frappe.cache.make_key(f"lms-rl:{frappe.form_dict.cmd}:{identity}:{seconds}")
			if not frappe.cache.get(key):
				frappe.cache.setex(key, seconds, 0)
			if frappe.cache.incrby(key, 1) > allowed:
				frappe.throw(
					_("Too many requests from this account. Please try again in a few minutes."),
					frappe.RateLimitExceededError,
				)
			return fn(*args, **kwargs)

		return wrapper

	return decorator
