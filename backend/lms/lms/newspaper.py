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
	_ensure_newspaper_access()
	records = frappe.get_all(
		"Sales Newspaper",
		filters={"status": ["in", ["Sending", "Sent", "Failed"]]},
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
	)
	if not rows:
		return _("Selected Batch")
	return ", ".join(row.batch_title or row.batch for row in rows)


@frappe.whitelist()
def get_newspaper(name: str):
	_ensure_newspaper_access()
	doc = frappe.get_doc("Sales Newspaper", name)
	return {
		"name": doc.name,
		"title": doc.title,
		"content": doc.content,
		"image": doc.image,
		"target_type": doc.target_type,
		"batches": [{"batch": row.batch, "batch_title": row.batch_title} for row in doc.batches],
		"recipient_count": doc.recipient_count,
		"status": doc.status,
		"published_by": doc.published_by,
		"published_by_name": frappe.db.get_value("User", doc.published_by, "full_name"),
		"published_at": doc.published_at,
		"email_sent_count": doc.email_sent_count,
		"email_failed_count": doc.email_failed_count,
		"target_label": _target_label(doc),
	}


@frappe.whitelist()
def send_newspaper(
	title: str,
	content: str,
	target_type: str,
	batches=None,
	image: str | None = None,
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

	frappe.enqueue(
		"lms.lms.newspaper.deliver_newspaper_emails",
		queue="long",
		newspaper=doc.name,
		job_name=f"newspaper-{doc.name}",
	)

	return {
		"name": doc.name,
		"recipient_count": doc.recipient_count,
		"status": doc.status,
	}


def deliver_newspaper_emails(newspaper: str):
	doc = frappe.get_doc("Sales Newspaper", newspaper)
	recipients = resolve_recipient_emails(
		doc.target_type,
		[row.batch for row in doc.batches],
	)

	if not recipients:
		doc.db_set({"status": "Failed", "email_failed_count": 0, "email_sent_count": 0})
		return

	sent = 0
	failed = 0
	subject = f"[{BRAND_NAME}] {doc.title}"
	image_url = get_url(doc.image) if doc.image else None
	sender_email = frappe.db.get_value("User", doc.published_by, "email")
	outgoing_email = frappe.get_cached_value(
		"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email"
	)
	primary_recipient = sender_email or outgoing_email or frappe.conf.get("mail_login")

	for i in range(0, len(recipients), EMAIL_BATCH_SIZE):
		chunk = recipients[i : i + EMAIL_BATCH_SIZE]
		try:
			frappe.sendmail(
				recipients=[primary_recipient] if primary_recipient else chunk[:1],
				bcc=chunk,
				subject=subject,
				template="newspaper_notification",
				args={
					"title": doc.title,
					"content": doc.content,
					"image_url": image_url,
					"brand_name": BRAND_NAME,
					"target_label": _target_label(doc),
				},
				retry=3,
				delayed=True,
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
