import frappe


def extend_lesson_upload_limit():
	"""Match lesson multipart uploads to the standard file upload size limit."""
	if not frappe.request:
		return
	path = frappe.request.path or ""
	if "upload_and_create_lesson" not in path and "sales_viva.sarvam_stt" not in path and "sales_viva.submit_audio" not in path:
		return
	from frappe.core.api.file import get_max_file_size

	limit = get_max_file_size()
	if "sales_viva.sarvam_stt" in path or "sales_viva.submit_audio" in path:
		limit = max(limit, 8 * 1024 * 1024)
	frappe.request.max_content_length = limit


def allow_sarvam_viva_csrf():
	"""Standalone /viva HTML is not a Frappe desk page; accept its POSTs."""
	if not frappe.request:
		return
	path = frappe.request.path or ""
	if "lms.lms.sales_viva." in path:
		frappe.flags.ignore_csrf = True


def rewrite_progress_like_filters():
	"""Rewrite MariaDB-era progress LIKE filters (MySQL/Postgres-safe)."""
	if not frappe.form_dict:
		return

	doctype = frappe.form_dict.get("doctype")
	filters = frappe.form_dict.get("filters")
	if not filters:
		return

	# Only rewrite enrollment progress filters (desk workspace shortcuts / list counts)
	if doctype and doctype not in ("LMS Enrollment",):
		# Still rewrite if filters clearly target progress LIKE — covers nested calls
		if "progress" not in str(filters) or "like" not in str(filters).lower():
			return
	elif "progress" not in str(filters) or "like" not in str(filters).lower():
		return

	import json

	try:
		parsed = json.loads(filters) if isinstance(filters, str) else filters
	except (TypeError, ValueError):
		return

	changed = False

	def _is_completion_like(op, value):
		op_l = str(op or "").lower()
		val = str(value or "")
		return op_l == "like" and "100" in val

	if isinstance(parsed, dict):
		prog = parsed.get("progress")
		if isinstance(prog, (list, tuple)) and len(prog) >= 2 and _is_completion_like(prog[0], prog[1]):
			parsed["progress"] = [">=", 100]
			changed = True
	elif isinstance(parsed, list):
		for i, item in enumerate(parsed):
			if not isinstance(item, (list, tuple)) or len(item) < 4:
				continue
			# ["LMS Enrollment", "progress", "like", "%100%"] or ["progress", "like", "%100%"]
			if item[1] == "progress" and _is_completion_like(item[2], item[3]):
				parsed[i] = [item[0], "progress", ">=", 100] + list(item[4:])
				changed = True
			elif item[0] == "progress" and _is_completion_like(item[1], item[2]):
				parsed[i] = ["progress", ">=", 100] + list(item[3:])
				changed = True

	if changed:
		frappe.form_dict["filters"] = json.dumps(parsed)
