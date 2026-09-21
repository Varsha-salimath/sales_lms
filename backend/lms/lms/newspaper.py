# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

"""LMS Newspaper — admin broadcast to learners via Frappe email queue."""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, get_url, now_datetime, strip_html

from lms.lms.branding import BRAND_NAME

MAX_TITLE_LENGTH = cint(frappe.conf.get("newspaper_max_title_length") or 200)
MAX_CONTENT_LENGTH = cint(frappe.conf.get("newspaper_max_content_length") or 5000)
EMAIL_BATCH_SIZE = cint(frappe.conf.get("newspaper_email_batch_size") or 500)


def _ensure_newspaper_access():
	from lms.lms.api import _ensure_analytics_access

	_ensure_analytics_access()


def _is_newspaper_manager() -> bool:
	if frappe.session.user == "Guest":
		return False
	roles = set(frappe.get_roles())
	return not roles.isdisjoint(
		{"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}
	)


def _ensure_logged_in():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)


def _strip_content_html(content: str) -> str:
	if not content:
		return ""
	return strip_html(content).strip()


def _validate_newspaper_payload(title: str, content: str, target_type: str, batches=None):
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Title is required."))
	if len(title) > MAX_TITLE_LENGTH:
		frappe.throw(_("Title cannot exceed {0} characters.").format(MAX_TITLE_LENGTH))

	plain = _strip_content_html(content)
	if not plain:
		frappe.throw(_("Message content is required."))
	if len(plain) > MAX_CONTENT_LENGTH:
		frappe.throw(_("Message cannot exceed {0} characters.").format(MAX_CONTENT_LENGTH))

	if target_type not in ("All Learners", "Selected Batch"):
		frappe.throw(_("Invalid target audience."))

	if target_type == "Selected Batch":
		batches = batches or []
		if not batches:
			frappe.throw(_("Select at least one batch."))


def resolve_recipient_emails(target_type: str, batches=None) -> list[str]:
	"""Return unique enabled learner emails for the selected audience."""
	batches = batches or []

	if target_type == "All Learners":
		user_ids = frappe.get_all(
			"Has Role",
			filters={"role": "LMS Student", "parenttype": "User"},
			pluck="parent",
		)
	else:
		if not batches:
			return []
		user_ids = frappe.get_all(
			"LMS Batch Enrollment",
			filters={"batch": ["in", batches]},
			pluck="member",
		)

	if not user_ids:
		return []

	user_ids = list(set(user_ids))
	emails = frappe.get_all(
		"User",
		filters={"name": ["in", user_ids], "enabled": 1, "user_type": "Website User"},
		pluck="email",
	)
	return sorted({email for email in emails if email})


def _target_label(doc) -> str:
	if doc.target_type == "All Learners":
		return _("All Learners")
	titles = [row.batch_title or row.batch for row in doc.batches]
	return ", ".join(titles) if titles else _("Selected Batch")


@frappe.whitelist()
def get_newspaper_limits():
	_ensure_newspaper_access()
	return {
		"max_title_length": MAX_TITLE_LENGTH,
		"max_content_length": MAX_CONTENT_LENGTH,
	}


@frappe.whitelist()
def get_newspaper_batches():
	_ensure_newspaper_access()
	return frappe.get_all(
		"LMS Batch",
		fields=["name", "title"],
		order_by="title asc",
	)


@frappe.whitelist()
def get_newspaper_recipient_count(target_type: str, batches=None):
	_ensure_newspaper_access()
	if isinstance(batches, str):
		batches = json.loads(batches) if batches else []
	return {
		"count": len(resolve_recipient_emails(target_type, batches)),
	}


@frappe.whitelist()
def get_newspapers():
	_ensure_logged_in()
	if _is_newspaper_manager():
		statuses = ["Sending", "Sent", "Failed"]
	else:
		statuses = ["Sending", "Sent"]
	records = frappe.get_all(
		"Sales Newspaper",
		filters={"status": ["in", statuses]},
		fields=[
			"name",
			"title",
			"content",
			"image",
			"target_type",
			"recipient_count",
			"status",
			"published_by",
			"published_at",
			"email_sent_count",
			"email_failed_count",
		],
		order_by="published_at desc",
		limit=100,
		ignore_permissions=True,
	)

	for row in records:
		row["content_preview"] = _strip_content_html(row.pop("content", "") or "")[:180]
		row["published_by_name"] = frappe.db.get_value("User", row.published_by, "full_name")
		row["target_label"] = (
			_("All Learners")
			if row.target_type == "All Learners"
			else _get_batch_labels_for_newspaper(row.name)
		)

	return records


def _get_batch_labels_for_newspaper(name: str) -> str:
	rows = frappe.get_all(
		"Sales Newspaper Batch",
		filters={"parent": name},
		fields=["batch_title", "batch"],
		ignore_permissions=True,
	)
	if not rows:
		return _("Selected Batch")
	return ", ".join(row.batch_title or row.batch for row in rows)


@frappe.whitelist()
def get_newspaper(name: str):
	_ensure_logged_in()
	if not frappe.db.exists("Sales Newspaper", name):
		frappe.throw(_("Newsletter not found."), frappe.DoesNotExistError)
	rows = frappe.get_all(
		"Sales Newspaper",
		filters={"name": name},
		fields=[
			"name",
			"title",
			"content",
			"image",
			"target_type",
			"recipient_count",
			"status",
			"published_by",
			"published_at",
			"email_sent_count",
			"email_failed_count",
		],
		limit=1,
		ignore_permissions=True,
	)
	row = rows[0] if rows else None
	if not row:
		frappe.throw(_("Newsletter not found."), frappe.DoesNotExistError)
	if not _is_newspaper_manager() and row.status not in ("Sending", "Sent"):
		frappe.throw(_("Newsletter not found."), frappe.PermissionError)
	batches = frappe.get_all(
		"Sales Newspaper Batch",
		filters={"parent": name},
		fields=["batch", "batch_title"],
		ignore_permissions=True,
	)
	doc = frappe._dict({**row, "batches": [frappe._dict(b) for b in batches]})
	return {
		"name": doc.name,
		"title": doc.title,
		"content": doc.content,
		"image": doc.image,
		"target_type": doc.target_type,
		"batches": [{"batch": b.batch, "batch_title": b.batch_title} for b in doc.batches],
		"recipient_count": doc.recipient_count,
		"status": doc.status,
		"published_by": doc.published_by,
		"published_by_name": frappe.db.get_value("User", doc.published_by, "full_name"),
		"published_at": doc.published_at,
		"email_sent_count": doc.email_sent_count,
		"email_failed_count": doc.email_failed_count,
		"target_label": _target_label(doc),
	}


def _build_newsletter_email_content(doc) -> str:
	parts = []
	if doc.image:
		parts.append(
			f'<p><img src="{get_url(doc.image)}" alt="" style="max-width:100%;height:auto;border-radius:8px;"></p>'
		)
	parts.append(doc.content or "")
	return "".join(parts)


@frappe.whitelist()
def send_newspaper(
	title: str,
	content: str,
	target_type: str,
	batches=None,
	image: str | None = None,
	reply_to: str | None = None,
):
	_ensure_newspaper_access()

	if isinstance(batches, str):
		batches = json.loads(batches) if batches else []

	_validate_newspaper_payload(title, content, target_type, batches)

	recipients = resolve_recipient_emails(target_type, batches)
	if not recipients:
		frappe.throw(_("No eligible learners found for the selected audience."))

	doc = frappe.new_doc("Sales Newspaper")
	doc.title = title.strip()
	doc.content = content
	doc.image = image
	doc.target_type = target_type
	doc.recipient_count = len(recipients)
	doc.status = "Sending"
	doc.published_by = frappe.session.user
	doc.published_at = now_datetime()

	if target_type == "Selected Batch":
		for batch_name in batches:
			doc.append("batches", {"batch": batch_name})

	doc.insert(ignore_permissions=True)

	reply_to = (reply_to or frappe.db.get_value("User", doc.published_by, "email") or "").strip()
	if not reply_to:
		frappe.throw(_("Reply-To email is required."))

	frappe.enqueue(
		"lms.lms.newspaper.deliver_newspaper_emails",
		queue="long",
		newspaper=doc.name,
		reply_to=reply_to,
		job_name=f"newspaper-{doc.name}",
	)

	return {
		"name": doc.name,
		"recipient_count": doc.recipient_count,
		"status": doc.status,
	}


def deliver_newspaper_emails(newspaper: str, reply_to: str | None = None):
	from frappe.core.doctype.communication.email import make as make_email_communication

	doc = frappe.get_doc("Sales Newspaper", newspaper)
	recipients = resolve_recipient_emails(
		doc.target_type,
		[row.batch for row in doc.batches],
	)

	if not recipients:
		doc.db_set({"status": "Failed", "email_failed_count": 0, "email_sent_count": 0})
		return

	reply_to = (reply_to or frappe.db.get_value("User", doc.published_by, "email") or "").strip()
	if not reply_to:
		doc.db_set({"status": "Failed", "email_failed_count": len(recipients), "email_sent_count": 0})
		return

	sent = 0
	failed = 0
	subject = f"[{BRAND_NAME}] {doc.title}"
	content = _build_newsletter_email_content(doc)
	reference_doctype = "Sales Newspaper"
	reference_name = doc.name
	if doc.target_type == "Selected Batch" and doc.batches:
		reference_doctype = "LMS Batch"
		reference_name = doc.batches[0].batch

	for i in range(0, len(recipients), EMAIL_BATCH_SIZE):
		chunk = recipients[i : i + EMAIL_BATCH_SIZE]
		try:
			make_email_communication(
				recipients=reply_to,
				bcc=", ".join(chunk),
				subject=subject,
				content=content,
				doctype=reference_doctype,
				name=reference_name,
				send_email=1,
				send_me_a_copy=0,
			)
			sent += len(chunk)
		except Exception:
			frappe.log_error(title=f"Newspaper email batch failed ({newspaper})")
			failed += len(chunk)

	status = "Sent" if failed == 0 else ("Failed" if sent == 0 else "Sent")
	doc.db_set(
		{
			"status": status,
			"email_sent_count": sent,
			"email_failed_count": failed,
			"recipient_count": len(recipients),
		}
	)


@frappe.whitelist()
def delete_newspaper(name: str):
	_ensure_newspaper_access()
	if not frappe.db.exists("Sales Newspaper", name):
		frappe.throw(_("Newsletter not found."), frappe.DoesNotExistError)
	frappe.db.delete("Sales Newspaper Comment", {"newspaper": name})
	frappe.delete_doc("Sales Newspaper", name, ignore_permissions=True)
	return {"deleted": name}


@frappe.whitelist()
def get_newspaper_comments(newspaper: str):
	_ensure_logged_in()
	if not frappe.db.exists("Sales Newspaper", newspaper):
		frappe.throw(_("Newsletter not found."), frappe.DoesNotExistError)
	status = frappe.db.get_value("Sales Newspaper", newspaper, "status")
	if not _is_newspaper_manager() and status not in ("Sending", "Sent"):
		frappe.throw(_("Newsletter not found."), frappe.PermissionError)

	rows = frappe.get_all(
		"Sales Newspaper Comment",
		filters={"newspaper": newspaper},
		fields=[
			"name",
			"content",
			"author",
			"author_name",
			"parent_comment",
			"is_staff_reply",
			"creation",
		],
		order_by="creation asc",
		limit=500,
		ignore_permissions=True,
	)
	return rows


@frappe.whitelist()
def add_newspaper_comment(newspaper: str, content: str, parent_comment: str | None = None):
	_ensure_logged_in()
	content = (content or "").strip()
	if not content:
		frappe.throw(_("Comment cannot be empty."))
	if not frappe.db.exists("Sales Newspaper", newspaper):
		frappe.throw(_("Newsletter not found."), frappe.DoesNotExistError)
	status = frappe.db.get_value("Sales Newspaper", newspaper, "status")
	if not _is_newspaper_manager() and status not in ("Sending", "Sent"):
		frappe.throw(_("Newsletter not found."), frappe.PermissionError)
	if parent_comment and not frappe.db.exists("Sales Newspaper Comment", parent_comment):
		frappe.throw(_("Parent comment not found."))

	comment = frappe.get_doc(
		{
			"doctype": "Sales Newspaper Comment",
			"newspaper": newspaper,
			"content": content,
			"author": frappe.session.user,
			"parent_comment": parent_comment or None,
			"is_staff_reply": 1 if _is_newspaper_manager() else 0,
		}
	)
	comment.insert(ignore_permissions=True)
	return {
		"name": comment.name,
		"content": comment.content,
		"author": comment.author,
		"author_name": comment.author_name or frappe.db.get_value("User", comment.author, "full_name"),
		"parent_comment": comment.parent_comment,
		"is_staff_reply": comment.is_staff_reply,
		"creation": comment.creation,
	}
