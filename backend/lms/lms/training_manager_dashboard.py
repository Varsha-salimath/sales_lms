# Copyright (c) 2026, Varsity Education and contributors
"""Training Manager views: learners grouped by LMS batch."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate

from lms.lms import access
from lms.lms.utils import get_lms_route


def _ensure_batch_wise_access():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required."), frappe.PermissionError)
	if access.get_tier() >= access.INSTRUCTOR:
		return
	if access.training_manager_tree(frappe.session.user):
		return
	if access.is_training_manager():
		return
	frappe.throw(_("You do not have access to this view."), frappe.PermissionError)


def _readiness_by_email(emails: set[str]) -> dict[str, dict]:
	if not emails or not frappe.db.exists("DocType", "Sales OJT Certification Metric"):
		return {}
	from lms.lms.learner_report import DOCTYPE, FIELDS, enrich

	out = {}
	for row in frappe.get_all(
		DOCTYPE,
		filters={"email": ["in", list(emails)]},
		fields=FIELDS,
		order_by="modified desc",
	):
		key = (row.email or "").strip().lower()
		if not key or key in out:
			continue
		enriched = enrich(row)
		out[key] = {
			"metric_name": enriched.name,
			"readiness": enriched.readiness,
			"readiness_band": enriched.readiness_band,
			"stage": enriched.stage,
		}
	return out


@frappe.whitelist()
def get_learners_by_batch() -> dict:
	"""Batches with enrolled learners the current user manages as Training Manager."""
	_ensure_batch_wise_access()
	user = frappe.session.user
	member_filter: set[str] | None = None
	tree = access.training_manager_tree(user)
	if tree:
		member_filter = set(tree)
	elif access.get_tier() < access.INSTRUCTOR:
		return {"batches": [], "total_learners": 0}
	else:
		scope = access.get_visible_members(user)
		if scope is not access.EVERYONE:
			member_filter = set(scope or [])

	filters: dict = {}
	if member_filter is not None:
		if not member_filter:
			return {"batches": [], "total_learners": 0}
		filters["member"] = ["in", sorted(member_filter)]

	enrollments = frappe.get_all(
		"LMS Batch Enrollment",
		filters=filters,
		fields=["name", "batch", "member", "member_name", "creation"],
		order_by="creation desc",
		limit_page_length=0,
	)

	if not enrollments:
		return {"batches": [], "total_learners": 0}

	from lms.lms.content_scope import allowed_names

	allowed_batches = allowed_names("LMS Batch", user)
	if allowed_batches is not access.EVERYONE:
		allowed_batches = set(allowed_batches or [])
		enrollments = [e for e in enrollments if e.batch in allowed_batches]

	if not enrollments:
		return {"batches": [], "total_learners": 0}

	by_batch: dict[str, list] = defaultdict(list)
	for row in enrollments:
		by_batch[row.batch].append(row)

	batch_ids = list(by_batch.keys())
	batch_rows = frappe.get_all(
		"LMS Batch",
		filters={"name": ["in", batch_ids]},
		fields=["name", "title", "start_date", "end_date", "published"],
	)
	meta = {b.name: b for b in batch_rows}

	emails = set()
	for rows in by_batch.values():
		for row in rows:
			email = frappe.db.get_value("User", row.member, "email") or row.member
			emails.add(email.strip().lower())
	readiness = _readiness_by_email(emails)

	def sort_key(batch_name: str):
		b = meta.get(batch_name)
		if not b or not b.start_date:
			return getdate("1900-01-01")
		return getdate(b.start_date)

	batches_out = []
	total = 0
	for batch_name in sorted(by_batch.keys(), key=sort_key, reverse=True):
		b = meta.get(batch_name)
		if not b:
			continue
		learners = []
		for enr in by_batch[batch_name]:
			email = (frappe.db.get_value("User", enr.member, "email") or enr.member or "").strip().lower()
			metric = readiness.get(email) or {}
			learners.append(
				{
					"enrollment": enr.name,
					"member": enr.member,
					"member_name": enr.member_name or frappe.db.get_value("User", enr.member, "full_name"),
					"email": email,
					"enrolled_on": enr.creation,
					"readiness": metric.get("readiness"),
					"readiness_band": metric.get("readiness_band"),
					"stage": metric.get("stage"),
					"report_name": metric.get("metric_name"),
				}
			)
		total += len(learners)
		batches_out.append(
			{
				"batch": batch_name,
				"title": b.title or batch_name,
				"start_date": b.start_date,
				"end_date": b.end_date,
				"published": b.published,
				"learner_count": len(learners),
				"dashboard_link": get_lms_route(f"batches/{batch_name}#dashboard"),
				"learners": learners,
			}
		)

	return {"batches": batches_out, "total_learners": total}
