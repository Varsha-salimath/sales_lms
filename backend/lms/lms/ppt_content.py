# Copyright (c) 2026, InfinityLearn and contributors
# For license information, please see license.txt

"""Turn CRT Excel content links (PPT / Slides / PDF / video / forms) into lesson bodies.

The classroom timetable is not the lesson. Unique decks and assessments are.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from frappe.utils import escape_html

GOOGLE_SLIDES_RE = re.compile(
	r"https://docs\.google\.com/presentation/d/([A-Za-z0-9_-]+)",
	re.I,
)
GOOGLE_FORM_RE = re.compile(
	r"https://(?:docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform[^\s]*|forms\.gle/[A-Za-z0-9]+)",
	re.I,
)
SHAREPOINT_RE = re.compile(r"https://[^\s]*sharepoint\.com/[^\s]+", re.I)
SKIP_TOPIC_RE = re.compile(
	r"(attendance|introduction of participants|lets know each other|let's know each other|"
	r"recap of day|checking laptop)",
	re.I,
)
IFRAME_HTML = (
	"<iframe src=\"{src}\" width=\"100%\" height=\"{height}\" "
	"style=\"border:1px solid #d7e4f7;border-radius:16px;background:#fff\" "
	"allowfullscreen allow=\"autoplay; clipboard-write; encrypted-media\"></iframe>"
)


def _hash(text: str) -> str:
	return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:8]


def _slug(text: str) -> str:
	slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
	return (slug[:40] or "lesson").strip("-")


def is_schedule_only(session: dict) -> bool:
	if session.get("session_type") in {"break", "lunch"}:
		return True
	# CRT 5 is operational (calling / live class / certificate) — keep it.
	if int(session.get("day_number") or 0) == 5:
		return False
	if session.get("session_type") in {"calling", "activity", "assessment"}:
		return False
	topic = session.get("topic") or ""
	if SKIP_TOPIC_RE.search(topic.split("\n")[0].strip()):
		return True
	return False


def classify_url(url: str) -> str:
	u = (url or "").lower()
	if GOOGLE_SLIDES_RE.search(url or ""):
		return "slides"
	if GOOGLE_FORM_RE.search(url or "") or "docs.google.com/forms" in u:
		return "form"
	if "sharepoint.com/:p:" in u or u.endswith(".pptx") or "presentation" in u:
		return "ppt"
	if "sharepoint.com/:v:" in u:
		return "video"
	if "sharepoint.com/:b:" in u or u.endswith(".pdf"):
		return "pdf"
	if "sharepoint.com/:x:" in u:
		return "sheet"
	if "sharepoint.com/:f:" in u:
		return "folder"
	if "sharepoint.com/" in u:
		return "sharepoint"
	if "forms.gle" in u:
		return "form"
	if "leadsquared.com" in u or "teams.microsoft.com" in u:
		return "link"
	if "infinitylearn.com" in u:
		return "web"
	return "link"


def primary_asset_url(links: list[dict]) -> str:
	if not links:
		return ""
	ranked = ("ppt", "slides", "video", "pdf", "folder", "sheet", "form", "sharepoint", "web", "link")
	for kind in ranked:
		for link in links:
			if classify_url(link.get("url") or "") == kind:
				return link["url"]
	return links[0].get("url") or ""


def identity_key(session: dict) -> str:
	url = primary_asset_url(session.get("content_links") or [])
	if url:
		parsed = urlparse(url)
		# Ignore share token noise so the same Target Exams PPT collapses to one lesson.
		base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
		return f"url:{base.lower()}"
	return f"topic:{_slug(session.get('topic') or '')}-{session.get('day_number')}"


def embed_src(url: str) -> str:
	kind = classify_url(url)
	if kind == "slides":
		match = GOOGLE_SLIDES_RE.search(url)
		if match:
			return f"https://docs.google.com/presentation/d/{match.group(1)}/embed?start=false&loop=false&delayms=3000"
	if kind == "form":
		if "docs.google.com/forms" in url:
			base = url.split("?")[0]
			return f"{base}?embedded=true"
		return url
	# Office embedview works for PPT/PDF/Excel. It 404s on SharePoint Stream videos.
	if kind == "video":
		return url
	if "sharepoint.com" in url.lower():
		if re.search(r"[?&]action=", url):
			return url
		return url + ("&" if "?" in url else "?") + "action=embedview"
	if kind == "web":
		if url.startswith("http"):
			return url
		return f"https://{url}"
	return url


def embed_service(url: str) -> str:
	kind = classify_url(url)
	if kind == "slides":
		return "slidesPublic"
	if kind == "form":
		return "googleForms"
	if "sharepoint.com" in (url or "").lower():
		return "sharepoint"
	if kind == "web":
		return "webframe"
	return "webframe"


def _block_id(seed: str) -> str:
	return _hash(seed)[:10]


def _header(text: str, level: int = 2, seed: str = "") -> dict:
	return {
		"id": _block_id(seed or text),
		"type": "header",
		"data": {"text": escape_html(text), "level": level},
	}


def _markdown(text: str, seed: str = "") -> dict:
	return {
		"id": _block_id(seed or text[:40]),
		"type": "markdown",
		"data": {"text": text},
	}


def _embed(url: str, label: str) -> dict:
	src = embed_src(url)
	return {
		"id": _block_id(url),
		"type": "embed",
		"data": {
			"service": embed_service(url),
			"source": url,
			"embed": src,
			"width": 600,
			"height": 640,
			"caption": label or "",
		},
	}


def extract_pptx_slides(data: bytes) -> list[dict]:
	slides = []
	ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
	try:
		with zipfile.ZipFile(io.BytesIO(data)) as archive:
			names = sorted(
				n for n in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)
			)
			for name in names:
				root = ET.fromstring(archive.read(name))
				texts = [node.text.strip() for node in root.iter(f"{ns}t") if node.text and node.text.strip()]
				if not texts:
					continue
				slides.append({"title": texts[0][:180], "points": texts[1:12]})
	except Exception:
		return []
	return slides


def fetch_google_slides(url: str) -> list[dict]:
	match = GOOGLE_SLIDES_RE.search(url or "")
	if not match:
		return []
	export = f"https://docs.google.com/presentation/d/{match.group(1)}/export/pptx"
	req = Request(export, headers={"User-Agent": "SalesLMS-CRT/1.0"})
	try:
		with urlopen(req, timeout=45) as response:
			payload = response.read()
	except Exception:
		return []
	if not payload.startswith(b"PK"):
		return []
	return extract_pptx_slides(payload)


def sharepoint_watch_url(url: str) -> str:
	"""Keep the Excel sharing link. Do not rewrite :v: links to guestaccess.aspx (that 404s)."""
	raw = (url or "").strip()
	raw = re.sub(r"[?&]action=embedview", "", raw)
	raw = re.sub(r"[?&]web=1", "", raw)
	if raw.endswith("?") or raw.endswith("&"):
		raw = raw[:-1]
	return raw


def _cover_blocks(session: dict) -> list[dict]:
	lines = [ln.strip(" -\t") for ln in (session.get("description") or "").splitlines() if ln.strip()]
	if not lines:
		return []
	topic = session.get("topic") or "cover"
	return [
		_header("What this deck covers", 3, f"cover-h-{topic}"),
		{
			"id": _block_id(f"cover-list-{topic}"),
			"type": "list",
			"data": {
				"style": "unordered",
				"items": [{"content": escape_html(ln), "items": []} for ln in lines],
			},
		},
	]


def _video_block(url: str, label: str) -> dict:
	watch = sharepoint_watch_url(url)
	safe = escape_html(watch)
	title = escape_html(label or "CRT video")
	return {
		"id": _block_id(f"watch-{url}"),
		"type": "paragraph",
		"data": {
			"text": (
				f'<a href="{safe}" target="_blank" rel="noopener noreferrer">'
				f"Watch video — {title}</a>"
				" (opens the Infinity Learn SharePoint recording; sign in with your IL account if asked)"
			)
		},
	}


def build_lesson_content(session: dict) -> str:
	topic = session.get("topic") or "CRT lesson"
	blocks = [_header(topic, 2, f"h-{topic}")]
	blocks.extend(_cover_blocks(session))

	seen = set()
	links = session.get("content_links") or []
	ranked = sorted(
		links,
		key=lambda row: (
			0 if classify_url(row.get("url") or "") in {"ppt", "slides", "video", "pdf"} else 1
		),
	)
	for link in ranked:
		url = link.get("url") or ""
		if not url or url in seen:
			continue
		seen.add(url)
		kind = classify_url(url)
		label = link.get("label") or kind.upper()
		if kind == "link":
			blocks.append(_markdown(f"**{escape_html(label)}:** [{escape_html(url)}]({url})", url))
			continue
		kind_label = {
			"ppt": "PowerPoint",
			"slides": "Slides",
			"video": "Video",
			"pdf": "PDF",
			"folder": "PPT folder",
			"sheet": "Workbook",
			"form": "Assessment",
			"web": "Website",
			"sharepoint": "Document",
		}.get(kind, "Content")
		blocks.append(_header(kind_label, 3, f"{kind}-{url}"))
		if kind == "video":
			blocks.append(_video_block(url, label))
			continue
		blocks.append(_embed(url, label))

	slides = session.get("extracted_slides") or []
	if slides:
		blocks.append(_header("Slide walkthrough", 3, f"walk-{topic}"))
		for index, slide in enumerate(slides, start=1):
			title = slide.get("title") or f"Slide {index}"
			points = slide.get("points") or []
			body = f"**Slide {index}. {escape_html(title)}**"
			if points:
				body += "\n\n" + "\n".join(f"- {escape_html(p)}" for p in points)
			blocks.append(_markdown(body, f"slide-{index}-{title}"))

	if len(blocks) == 1:
		blocks.append(_markdown("Content for this topic is still being attached from the CRT Excel.", topic))

	return json.dumps(
		{"time": int(datetime.now().timestamp() * 1000), "blocks": blocks, "version": "2.29.0"}
	)


def attach_extracted_slides(session: dict) -> None:
	for link in session.get("content_links") or []:
		if classify_url(link.get("url") or "") == "slides":
			session["extracted_slides"] = fetch_google_slides(link["url"])
			return


def to_curriculum(sessions: list[dict]) -> list[dict]:
	"""Drop timetable rows and collapse duplicate PPT links into one lesson per day."""
	merged: dict[tuple, dict] = {}
	order: list[tuple] = []

	for session in sessions:
		if is_schedule_only(session):
			continue
		links = session.get("content_links") or []
		# Day 5 and live-calling / certificate rows have no PPT — keep them as CRT 5.
		operational = session.get("session_type") in {"calling", "activity", "assessment"} or int(
			session.get("day_number") or 0
		) == 5
		if not links and not operational:
			continue
		key = (session["day_number"], identity_key(session))
		if key not in merged:
			clone = dict(session)
			clone["descriptions"] = [session.get("description") or ""]
			clone["source_rows"] = [session.get("excel_row")]
			merged[key] = clone
			order.append(key)
			continue
		existing = merged[key]
		desc = session.get("description") or ""
		if desc and desc not in existing["descriptions"]:
			existing["descriptions"].append(desc)
		for link in links:
			if link not in existing["content_links"]:
				existing["content_links"].append(link)
		existing["source_rows"].append(session.get("excel_row"))

	curriculum = []
	index_by_day: dict[int, int] = {}
	viewable = {"ppt", "slides", "video", "pdf", "folder", "sheet", "form", "web", "sharepoint"}
	for key in order:
		item = merged[key]
		has_asset = any(
			classify_url(link.get("url") or "") in viewable for link in item.get("content_links") or []
		)
		operational = item.get("session_type") in {"calling", "activity", "assessment"} or int(
			item.get("day_number") or 0
		) == 5
		if not has_asset and not operational:
			continue
		day = item["day_number"]
		index_by_day[day] = index_by_day.get(day, 0) + 1
		item["session_index"] = index_by_day[day]
		item["session_type"] = "session"
		item["description"] = "\n".join(d for d in item["descriptions"] if d)
		item["session_key"] = f"crt-d{day}-{_slug(item['topic'])}-{_hash(identity_key(item))}"
		item["time_label"] = ""
		item["stakeholder"] = ""
		item["duration_minutes"] = None
		attach_extracted_slides(item)
		curriculum.append(item)
	return curriculum
