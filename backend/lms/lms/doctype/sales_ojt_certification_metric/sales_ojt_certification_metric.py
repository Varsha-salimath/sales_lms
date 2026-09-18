# Copyright (c) 2026, Varsity Education and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from lms.lms.ojt_certification import STAGES, derive_product_avg, derive_stage, make_row_key


class SalesOJTCertificationMetric(Document):
	def validate(self):
		self._bind_learner()
		if self.flags.from_sheet_sync:
			return
		self._validate_admin_metrics()

	def before_save(self):
		self.email = (self.email or "").strip().lower()
		if not self.email:
			frappe.throw(_("Email is required"))
		self.row_key = make_row_key(self.email, self.batch_start)
		if self.flags.from_sheet_sync:
			self.product_avg = derive_product_avg(self)
			self.stage = derive_stage(self)
			return
		if self.product_avg in (None, ""):
			self.product_avg = derive_product_avg(self)
		if not self.stage:
			self.stage = derive_stage(self)

	def _bind_learner(self):
		if not self.learner:
			return
		user = frappe.db.get_value(
			"User",
			self.learner,
			["name", "full_name", "email"],
			as_dict=True,
		)
		if not user:
			frappe.throw(_("Selected learner was not found"))
		self.employee_name = user.full_name or user.name
		self.email = (user.email or user.name or "").strip().lower()

	def _validate_admin_metrics(self):
		if self.attendance_days not in (None, ""):
			days = cint(self.attendance_days)
			if days < 0:
				frappe.throw(_("Attendance must be 0 or greater"))
			self.attendance_days = days
		if self.ai_mock_score not in (None, ""):
			score = flt(self.ai_mock_score)
			if score < 0:
				frappe.throw(_("AI Mock must be 0 or greater"))
			self.ai_mock_score = score
		if self.audit_score not in (None, ""):
			score = flt(self.audit_score)
			if score < 0 or score > 20:
				frappe.throw(_("Audit score must be between 0 and 20"))
			self.audit_score = score
		if self.product_avg not in (None, ""):
			score = flt(self.product_avg)
			if score < 0 or score > 20:
				frappe.throw(_("Product average must be between 0 and 20"))
			self.product_avg = round(score, 2)
		if self.stage and self.stage not in STAGES:
			frappe.throw(_("Invalid stage"))
