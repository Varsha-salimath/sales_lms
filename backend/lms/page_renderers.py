"""Custom page renderers for LMS app.

Handles rendering of profile pages.
"""

import mimetypes
import os

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file


class SCORMRenderer(BaseRenderer):
	def can_render(self):
		return "scorm/" in self.path

	def _is_safe_path(self, path):
		scorm_root = os.path.realpath(os.path.join(frappe.local.site_path, "public", "scorm"))
		resolved = os.path.realpath(path)
		return resolved.startswith(scorm_root + os.sep) or resolved == scorm_root

	def _serve_file(self, path):
		f = open(path, "rb")
		response = Response(wrap_file(frappe.local.request.environ, f), direct_passthrough=True)
		response.mimetype = mimetypes.guess_type(path)[0]
		return response

	def render(self):
		path = os.path.join(frappe.local.site_path, "public", self.path.lstrip("/"))

		if not self._is_safe_path(path):
			raise frappe.PermissionError

		extension = os.path.splitext(path)[1]
		if not extension:
			path = f"{path}.html"

		# check if path exists and is actually a file and not a folder
		if os.path.exists(path) and os.path.isfile(path):
			return self._serve_file(path)
		else:
			path = path.replace(".html", "")
			if os.path.exists(path) and os.path.isdir(path):
				index_path = os.path.join(path, "index.html")
				if os.path.exists(index_path):
					return self._serve_file(index_path)
			elif not os.path.exists(path):
				chapter_folder = "/".join(self.path.split("/")[:3])
				chapter_folder_path = os.path.realpath(frappe.get_site_path("public", chapter_folder))
				file = path.split("/")[-1]
				correct_file_path = None

				if not self._is_safe_path(chapter_folder_path):
					raise frappe.PermissionError

				for root, _dirs, files in os.walk(chapter_folder_path):
					if file in files:
						correct_file_path = os.path.join(root, file)
						break

				if correct_file_path and self._is_safe_path(correct_file_path):
					return self._serve_file(correct_file_path)


from lms.lms.routing import SPA_TOP_LEVEL, is_valid_spa_path


class VivaDemoRenderer(BaseRenderer):
	"""CRT viva — Gemini Live native audio. Must run before the Vue SPA renderer."""

	def can_render(self):
		return (self.path or "").strip("/") in ("viva", "lms/viva")

	def render(self):
		html_path = os.path.join(os.path.dirname(__file__), "www", "viva.html")
		with open(html_path, encoding="utf-8") as f:
			html = f.read()
		response = Response(html)
		response.mimetype = "text/html"
		response.headers["Cache-Control"] = "no-store"
		return response


class SalesLmsSpaRenderer(BaseRenderer):
	"""Serve the Vue SPA at clean paths without stealing /login, /app, or Frappe www pages."""

	def can_render(self):
		path = (self.path or "").lstrip("/")
		if not path or not is_valid_spa_path(path):
			return False
		parts = path.split("/")
		first = parts[0]
		if first not in SPA_TOP_LEVEL:
			return False
		# Keep Frappe www/certificate.py for /courses/<course>/<certificate_id>
		if first == "courses" and len(parts) == 3 and parts[2] not in ("certification", "learn"):
			if frappe.db.exists("LMS Certificate", parts[2]):
				return False
		return True

	def render(self):
		from frappe.website.page_renderers.template_page import TemplatePage

		frappe.form_dict.app_path = (self.path or "").lstrip("/")
		return TemplatePage("_lms", self.http_status_code).render()
