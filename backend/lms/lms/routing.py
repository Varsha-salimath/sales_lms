# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""User-facing URL helpers: strip legacy /lms prefix; keep Frappe internals intact.

frappe.Redirect is unsafe in before_request (Frappe 16 renders a 301 error page).
Raise it from website_path_resolver / www get_context, where serve.py maps it to Location.
"""

import re
from urllib.parse import quote

import frappe

SPA_TOP_LEVEL = {
	"dashboard",
	"crt",
	"evaluation",
	"ojt",
	"sales-certificate",
	"admin",
	"home",
	"courses",
	"course",
	"course-feedback",
	"certificate",
	"batches",
	"billing",
	"statistics",
	"analytics",
	"analytics-dashboard",
	"ojt-certification-analytics",
	"library",
	"user",
	"job-openings",
	"job-opening",
	"certified-participants",
	"notifications",
	"quizzes",
	"quiz",
	"quiz-submissions",
	"quiz-submission",
	"programs",
	"assignments",
	"assignment-submission",
	"assignment-submissions",
	"persona",
	"programming-exercises",
	"search",
	"data-import",
	"newspaper",
	"reports",
	"team",
	"hello-ilians",
}

# Exact SPA paths the Vue router knows about (extra segments → invalid URL).
_ALLOWED_SPA_ROUTE_RES = tuple(
	re.compile(p)
	for p in (
		r"dashboard",
		r"crt/import",
		r"crt/session/[^/]+",
		r"crt/\d+",
		r"evaluation",
		r"ojt/[^/]+",
		r"ojt",
		r"sales-certificate",
		r"admin",
		r"home",
		r"courses",
		r"course/[^/]+/player",
		r"course/[^/]+",
		r"courses/[^/]+/learn/\d+-\d+/edit",
		r"courses/[^/]+/learn/\d+-\d+",
		r"courses/[^/]+/learn/[^/]+",
		r"courses/[^/]+/certification",
		r"courses/[^/]+",
		r"course-feedback/[^/]+",
		r"course-feedback",
		r"certificate/[^/]+",
		r"batches/details/[^/]+",
		r"batches/[^/]+/leaderboard",
		r"batches/[^/]+",
		r"batches",
		r"billing/[^/]+/[^/]+",
		r"statistics",
		r"analytics-dashboard",
		r"ojt-certification-analytics",
		r"analytics",
		r"newspaper/new",
		r"newspaper/[^/]+",
		r"newspaper",
		r"reports/[^/]+",
		r"reports",
		r"team",
		r"hello-ilians",
		r"library",
		r"user/[^/]+/certificates",
		r"user/[^/]+/roles",
		r"user/[^/]+/slots",
		r"user/[^/]+/schedule",
		r"user/[^/]+/mock-results",
		r"user/[^/]+",
		r"job-openings/[^/]+/applications",
		r"job-openings/[^/]+",
		r"job-openings",
		r"job-opening/[^/]+/edit",
		r"certified-participants",
		r"notifications",
		r"quizzes/[^/]+",
		r"quizzes",
		r"quiz/[^/]+",
		r"quiz-submissions/[^/]+",
		r"quiz-submission/[^/]+",
		r"programs/[^/]+",
		r"programs",
		r"assignments",
		r"assignment-submission/[^/]+/[^/]+",
		r"assignment-submissions",
		r"persona",
		r"programming-exercises/submissions",
		r"programming-exercises/[^/]+/submission/[^/]+",
		r"programming-exercises",
		r"search",
		r"data-import/doctype/[^/]+",
		r"data-import/[^/]+",
		r"data-import",
	)
)

SKIP_PREFIXES = (
	"/api/",
	"/app",
	"/assets/",
	"/files/",
	"/private/",
	"/socket.io",
	"/backups",
	"/rss.xml",
)

# Frappe www pages that must not pass through dynamic route maps (e.g. legacy /lms catch-all cache).
RESERVED_WWW_PATHS = frozenset(
	{
		"login",
		"logout",
		"signup",
		"forgot",
		"update-password",
		"update_profile",
		"me",
		"about",
		"contact",
		"error",
		"404",
		"app",
		"desk",
	}
)


def raise_page_redirect(location: str, status: int = 302):
	frappe.flags.redirect_location = location
	frappe.local.flags.redirect_location = location
	raise frappe.Redirect(status)


def _query_suffix(request) -> str:
	raw = getattr(request, "query_string", None) or b""
	if not raw:
		return ""
	decoded = raw.decode("utf-8", errors="ignore")
	return f"?{decoded}" if decoded else ""


def canonical_destination(path: str, is_guest: bool, query: str = "") -> str | None:
	"""Return a 302 target for `/`, `/lms`, and `/lms/<page>`. None = serve as-is."""
	path = path or "/"
	if path.startswith(SKIP_PREFIXES) or path == "/app":
		return None

	if path in ("/", ""):
		return ("/login" if is_guest else "/dashboard") + query

	if path != "/lms" and not path.startswith("/lms/"):
		return None

	rest = path[4:] or "/"
	if not rest.startswith("/"):
		rest = f"/{rest}"
	if rest in ("/", ""):
		return ("/login" if is_guest else "/dashboard") + query
	if is_guest:
		return login_url_with_redirect(rest)
	return rest + query


def strip_legacy_lms_prefix():
	"""Legacy before_request hook kept for backward compatibility.

	Canonical /lms/* and / redirects are handled by resolve_sales_lms_path via
	website_path_resolver. Do not raise frappe.Redirect here (unsafe in before_request).
	"""
	return None


def _is_desk_path(path: str) -> bool:
	path = (path or "").split("?", 1)[0].rstrip("/") or "/"
	return path in ("/app", "/desk") or path.startswith("/app/") or path.startswith("/desk/")


def block_desk_portal_routes():
	"""Keep Frappe Desk (/app, /desk) for configured admins only.

	Desk routes bypass the website path resolver, so LMS users otherwise see
	Frappe's generic "Not Permitted" page. Send everyone else to the SPA.
	"""
	request = getattr(frappe.local, "request", None)
	if not request or request.method not in ("GET", "HEAD"):
		return

	path = (request.path or "").split("?", 1)[0].rstrip("/") or "/"
	if not _is_desk_path(path):
		return

	from werkzeug.utils import redirect

	query = _query_suffix(request)

	if frappe.session.user == "Guest":
		target = "/login" + query
		return redirect(target, code=302)

	target = desk_redirect(path.lstrip("/"))
	if target:
		return redirect(target + query, code=302)

	return None


# Before login the only screens are sign-in and set-password; every other page bounces to /login.
# Enforced in resolve_sales_lms_path: Frappe ignores return values from before_request hooks.
GUEST_PAGES = frozenset({"login", "update-password", "logout"})


def guest_login_redirect(path: str | None) -> str | None:
	"""Where to send a guest asking for `path`; None when the page is allowed."""
	bare = (path or "").split("?", 1)[0].strip("/")
	if bare in GUEST_PAGES:
		return None
	if bare and bare != "dashboard" and is_valid_spa_path(bare):
		return login_url_with_redirect(f"/{bare}")
	return "/login"


# Desk (/desk, /app) is for the two master admins only; everyone else works inside the LMS.
# Override per site with "lms_desk_users": [...] in site_config.json.
DEFAULT_DESK_USERS = ("twinkle.garg@infinitylearn.com", "varsha.s@infinitylearn.com")
DESK_PREFIXES = ("desk", "app")


def desk_users() -> set:
	configured = frappe.conf.get("lms_desk_users")
	return {"Administrator", *(configured if configured else DEFAULT_DESK_USERS)}


def desk_redirect(path: str | None) -> str | None:
	"""Where to send a signed-in user who may not use Desk; None when allowed."""
	head = (path or "").split("?", 1)[0].strip("/").split("/", 1)[0]
	if head not in DESK_PREFIXES:
		return None
	if frappe.session.user in ("Guest", *desk_users()):
		return None
	return "/dashboard"


def _reserved_www_path(path: str | None) -> str | None:
	"""Return path unchanged when it is a Frappe www route (login, signup, etc.)."""
	bare = (path or "").strip("/ ")
	if not bare:
		return None
	head = bare.split("/")[0]
	if head in RESERVED_WWW_PATHS:
		return bare
	return None


def is_valid_spa_path(path: str | None) -> bool:
	bare = (path or "").strip("/")
	if not bare:
		return False
	return any(pattern.match(bare) for pattern in _ALLOWED_SPA_ROUTE_RES)


def invalid_spa_redirect(path: str | None, is_guest: bool, query: str = "") -> str | None:
	"""Redirect garbage SPA URLs (e.g. /analytics/random) away from the shell."""
	bare = (path or "").strip("/")
	if not bare:
		return None
	first = bare.split("/")[0]
	if first not in SPA_TOP_LEVEL:
		return None
	if is_valid_spa_path(bare):
		return None
	return ("/login" if is_guest else "/dashboard") + query


def resolve_sales_lms_path(path):
	"""Auth-aware canonical redirects, then Frappe's normal website path resolution."""
	from frappe.website.path_resolver import resolve_path

	request = getattr(frappe.local, "request", None)
	if frappe.session.user == "Guest" and (not request or request.method in ("GET", "HEAD")):
		target = guest_login_redirect(path)
		if target:
			raise_page_redirect(target)

	if not request or request.method in ("GET", "HEAD"):
		target = desk_redirect(path)
		if target:
			raise_page_redirect(target)

		bare_login = (path or "").strip("/").split("/")[0]
		if bare_login == "login" and frappe.session.user != "Guest":
			raise_page_redirect(login_redirect_from_request())

	reserved = _reserved_www_path(path)
	if reserved:
		return reserved

	if request and request.method not in ("GET", "HEAD"):
		return resolve_path(path)

	raw = path or "/"
	if not raw.startswith("/"):
		raw = f"/{raw}"
	normalized = "/" if raw == "/" else raw.rstrip("/")
	query = _query_suffix(request) if request else ""
	is_guest = frappe.session.user == "Guest"
	target = canonical_destination(normalized, is_guest, query)
	current = normalized.split("?", 1)[0]
	if target and target.split("?", 1)[0] != current:
		raise_page_redirect(target)

	bare_path = normalized.strip("/")
	first_segment = bare_path.split("/")[0] if bare_path else ""
	if first_segment in ("app", "desk") and is_guest:
		raise_page_redirect("/login" + query)

	invalid = invalid_spa_redirect(bare_path, is_guest, query)
	if invalid:
		raise_page_redirect(invalid)

	return resolve_path(path)


def login_redirect_from_request():
	"""Safe post-login destination from redirect-to, else /dashboard."""
	raw = (
		frappe.form_dict.get("redirect-to")
		or frappe.form_dict.get("redirect_to")
		or ""
	)
	return sanitize_user_facing_path(raw) or "/dashboard"


def sanitize_user_facing_path(url: str | None) -> str | None:
	if not url:
		return None
	url = str(url).strip()
	if not url.startswith("/") or url.startswith("//"):
		return None
	if url.startswith(("/api", "/app", "/assets", "/files", "/private", "/desk")):
		return None
	if url in ("/lms", "/lms/"):
		return "/dashboard"
	if url.startswith("/lms/"):
		return url[4:] or "/dashboard"
	if url in ("/", "/login"):
		return "/dashboard"
	return url


def login_url_with_redirect(next_path: str | None = None) -> str:
	target = sanitize_user_facing_path(next_path)
	if not target or target in ("/", "/login"):
		return "/login"
	return f"/login?redirect-to={quote(target, safe='/')}"


def get_website_user_home_page(user: str | None = None) -> str:
	"""Backup if GET `/` reaches Frappe home_page resolution without a 302."""
	if not user or user == "Guest":
		return "login"
	return "dashboard"
