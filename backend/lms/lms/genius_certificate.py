# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Render Genius Copilot certificates as full-bleed A4 landscape PDF/PNG."""

from __future__ import annotations

import io
import json
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import formatdate, getdate


COURSE_BODY_TITLE = "AI for Educator Productivity"


def _template_path() -> Path:
	return Path(frappe.get_app_path("lms", "public", "images", "genius-certificate-copilot.png"))


def _layout_path() -> Path:
	return Path(frappe.get_app_path("lms", "public", "images", "genius-certificate-layout.json"))


def _load_layout() -> dict:
	path = _layout_path()
	if path.is_file():
		return json.loads(path.read_text(encoding="utf-8"))
	# Sensible defaults for 3x A4 landscape render (~2526x1786)
	return {
		"width": 2526,
		"height": 1786,
		"name_line_y": int(1786 * 0.52),
		"name_font_size": 96,
		"date_line_y": int(1786 * 0.82),
		"date_left": int(2526 * 0.12),
		"date_right": int(2526 * 0.27),
		"date_font_size": 38,
	}


def _font(bold: bool, size: int):
	from PIL import ImageFont

	candidates = (
		["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]
		if bold
		else ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]
	)
	# Common container / Windows paths
	search = [
		"/usr/share/fonts/truetype/dejavu/",
		"/usr/share/fonts/truetype/liberation/",
		"/usr/share/fonts/truetype/freefont/",
		"C:/Windows/Fonts/",
	]
	names = (
		["arialbd.ttf", "ARIALBD.TTF", "DejaVuSans-Bold.ttf"]
		if bold
		else ["arial.ttf", "ARIAL.TTF", "DejaVuSans.ttf"]
	)
	for folder in search:
		for name in names:
			p = Path(folder) / name
			if p.is_file():
				return ImageFont.truetype(str(p), size)
	return ImageFont.load_default()


def format_completion_date(value) -> str:
	"""Return date like '14 August 2026'."""
	if not value:
		value = frappe.utils.nowdate()
	return formatdate(getdate(value), "dd MMMM yyyy")


def get_learner_full_name(member: str | None = None, fallback: str | None = None) -> str:
	name = fallback
	if member:
		name = frappe.db.get_value("User", member, "full_name") or name or member
	return (name or "").strip()


def render_certificate_image(learner_full_name: str, completion_date) -> bytes:
	"""Return PNG bytes of the completed certificate (full landscape artwork)."""
	from PIL import Image, ImageDraw

	template = _template_path()
	if not template.is_file():
		frappe.throw(_("Certificate template image is missing."))

	layout = _load_layout()
	im = Image.open(template).convert("RGB")
	w, h = im.size
	draw = ImageDraw.Draw(im)

	name = (learner_full_name or "").strip().upper() or "LEARNER"
	date_text = format_completion_date(completion_date)

	name_font = _font(True, int(layout.get("name_font_size") or max(52, w // 26)))
	date_font = _font(True, int(layout.get("date_font_size") or max(24, w // 65)))

	line_y = int(layout.get("name_line_y") or int(h * 0.52))
	nb = draw.textbbox((0, 0), name, font=name_font)
	nx = (w - (nb[2] - nb[0])) // 2
	ny = line_y - (nb[3] - nb[1]) - max(8, h // 100)
	draw.text((nx, ny), name, fill=(20, 20, 20), font=name_font)

	date_left = int(layout.get("date_left") or int(w * 0.12))
	date_right = int(layout.get("date_right") or int(w * 0.27))
	date_line_y = int(layout.get("date_line_y") or int(h * 0.82))
	db = draw.textbbox((0, 0), date_text, font=date_font)
	dw = db[2] - db[0]
	dx = date_left + ((date_right - date_left) - dw) // 2
	dy = date_line_y - (db[3] - db[1]) - max(6, h // 120)
	draw.text((dx, dy), date_text, fill=(20, 20, 20), font=date_font)

	buf = io.BytesIO()
	im.save(buf, format="PNG", optimize=True)
	return buf.getvalue()


def render_certificate_pdf(learner_full_name: str, completion_date) -> bytes:
	"""Return A4 landscape PDF bytes with the certificate image filling the page."""
	import img2pdf

	png = render_certificate_image(learner_full_name, completion_date)
	a4_landscape = (img2pdf.mm_to_pt(297), img2pdf.mm_to_pt(210))
	layout_fun = img2pdf.get_layout_fun(a4_landscape)
	return img2pdf.convert(png, layout_fun=layout_fun)


def render_certificate_for_doc(doc) -> tuple[bytes, bytes, str, str]:
	"""Return (pdf_bytes, png_bytes, learner_name, completion_date_str)."""
	member = getattr(doc, "member", None)
	learner = get_learner_full_name(member, getattr(doc, "member_name", None))
	issue_date = getattr(doc, "issue_date", None)
	pdf = render_certificate_pdf(learner, issue_date)
	png = render_certificate_image(learner, issue_date)
	return pdf, png, learner, format_completion_date(issue_date)
