"""Always send users to the Sales LMS login page after logout."""

import frappe

from lms.lms.routing import raise_page_redirect

no_cache = True


def get_context(context):
	frappe.local.login_manager.logout()
	raise_page_redirect("/login")
