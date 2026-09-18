"""Sales LMS branded login — extends Frappe login context, no Frappe branding."""

import frappe
from frappe.www.login import get_context as frappe_get_context

from lms.lms.branding import BRAND_NAME

no_cache = True

IL_FAVICON = "/assets/lms/frontend/favicon.png"
IL_LOGO = "/assets/lms/images/il-logo-white.svg"
TERMS_URL = "https://www.infinitylearn.com/terms-and-conditions"
PRIVACY_URL = "https://www.infinitylearn.com/privacy-policy"


def get_context(context):
	if frappe.session.user != "Guest":
		from lms.lms.routing import login_redirect_from_request, raise_page_redirect

		raise_page_redirect(login_redirect_from_request())

	frappe_get_context(context)

	context.title = f"{BRAND_NAME} — Login"
	context.app_name = BRAND_NAME
	context.logo = IL_LOGO
	context.favicon = IL_FAVICON
	context.body_class = (context.get("body_class") or "") + " il-auth-page"
	context.il_terms_url = TERMS_URL
	context.il_privacy_url = PRIVACY_URL
	context.show_footer_on_login = False

	return context
