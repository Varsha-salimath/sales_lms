# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import nowdate
from frappe.utils.telemetry import capture


class LMSCertificate(Document):
	def validate(self):
		self.validate_criteria()
		self.validate_duplicate_certificate()

	def autoname(self):
		self.name = make_autoname("hash", self.doctype)

	def after_insert(self):
		capture("certificate_issued", "lms")
		self.send_certification_email()

	def send_certification_email(self):
		outgoing_email_account = frappe.get_cached_value(
			"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
		)
		if outgoing_email_account or frappe.conf.get("mail_login"):
			self.send_mail()

	def send_mail(self):
		subject = _("Congratulations on getting certified!")
		template = "certification"
		custom_template = frappe.db.get_single_value("LMS Settings", "certification_template")

		args = {
			"member_name": self.member_name,
			"course_name": self.course,
			"course_title": frappe.db.get_value("LMS Course", self.course, "title"),
			"name": self.name,
			"template": self.template,
		}

		if custom_template:
			email_template = get_email_template(custom_template, args)
			subject = email_template.get("subject")
			content = email_template.get("message")
		frappe.sendmail(
			recipients=self.member,
			subject=subject,
			template=template if not custom_template else None,
			content=content if custom_template else None,
			args=args,
			header=[subject, "green"],
		)

	def validate_criteria(self):
		self.validate_role_of_owner()
		if self.batch_name:
			self.validate_batch_enrollment()
		elif self.course:
			self.validate_course_enrollment()

	def validate_role_of_owner(self):
		roles = frappe.get_roles()
		is_admin = any(role in roles for role in ["Moderator", "Course Creator", "Batch Evaluator"])
		if not self.course and not self.batch_name and not is_admin:
			frappe.throw(_("Course or Batch is required to issue a certificate."))

	def validate_batch_enrollment(self):
		if self.batch_name:
			is_enrolled = frappe.db.exists(
				"LMS Batch Enrollment", {"batch": self.batch_name, "member": self.member}
			)
			if not is_enrolled:
				frappe.throw(_("Certification cannot be issued as the member is not enrolled in this batch."))

	def validate_course_enrollment(self):
		if self.course:
			is_enrolled = frappe.db.exists("LMS Enrollment", {"course": self.course, "member": self.member})
			if not is_enrolled:
				frappe.throw(
					_("Certification cannot be issued as the member is not enrolled in this course.")
				)

			completion_certificate = frappe.db.get_value("LMS Course", self.course, "enable_certification")
			if completion_certificate:
				from frappe.utils import flt
				from lms.lms.utils import get_course_progress

				progress = flt(get_course_progress(self.course, self.member) or 0)
				if progress < 100:
					frappe.throw(
						_("Certification cannot be issued as the member has not completed the course.")
					)

	def validate_duplicate_certificate(self):
		self.validate_course_duplicates()
		self.validate_batch_duplicates()

	def validate_course_duplicates(self):
		if self.course:
			course_duplicates = frappe.get_all(
				"LMS Certificate",
				filters={
					"member": self.member,
					"name": ["!=", self.name],
					"course": self.course,
				},
				fields=["name", "course", "course_title"],
			)
			if len(course_duplicates):
				full_name = frappe.db.get_value("User", self.member, "full_name")
				frappe.throw(
					_("{0} is already certified for the course {1}").format(
						full_name, course_duplicates[0].course_title
					)
				)

	def validate_batch_duplicates(self):
		if self.batch_name:
			batch_duplicates = frappe.get_all(
				"LMS Certificate",
				filters={
					"member": self.member,
					"name": ["!=", self.name],
					"batch_name": self.batch_name,
				},
				fields=["name", "batch_name", "batch_title"],
			)
			if len(batch_duplicates):
				full_name = frappe.db.get_value("User", self.member, "full_name")
				frappe.throw(
					_("{0} is already certified for the batch {1}").format(
						full_name, batch_duplicates[0].batch_title
					)
				)

	def on_update(self):
		# Member may view/print their certificate; write remains staff-only.
		frappe.share.add_docshare(
			self.doctype,
			self.name,
			self.member,
			write=0,
			share=0,
			flags={"ignore_share_permission": True},
		)


def _is_certificate_staff(user: str | None = None) -> bool:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return bool(
		roles.intersection(
			{"System Manager", "Moderator", "Course Creator", "Batch Evaluator"}
		)
	)


def has_website_permission(doc, ptype, user, verbose=False):
	"""Website/print access: member or staff only — never Guest."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if ptype in ("read", "print", "select"):
		if doc.member == user:
			return True
		return _is_certificate_staff(user)
	if doc.member == user and ptype == "create":
		return True
	return False


def is_certified(course):
	certificate = frappe.get_all("LMS Certificate", {"member": frappe.session.user, "course": course})
	if len(certificate):
		return certificate[0].name
	return


@frappe.whitelist()
def create_certificate(course: str):
	certificate = is_certified(course)
	if certificate:
		return frappe.db.get_value(
			"LMS Certificate", certificate, ["name", "course", "template"], as_dict=True
		)

	else:
		validate_certification_eligibility(course)
		return issue_certificate_on_completion(course, frappe.session.user)


def get_genius_certificate_bg_uri():
	"""Return Copilot certificate background as a data URI (PDF-safe, no HTTP)."""
	import base64
	from pathlib import Path

	path = Path(frappe.get_app_path("lms", "public", "images", "genius-certificate-copilot.png"))
	if not path.is_file():
		frappe.throw(
			_(
				"Certificate template image is missing. Ensure genius-certificate-copilot.png is deployed."
			)
		)
	return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _pdf_reachable_host():
	"""Host wkhtmltopdf can reach from the backend container (Docker-local)."""
	return frappe.conf.get("pdf_host_name") or "http://frontend:8080"


@frappe.whitelist()
def download_pdf(
	doctype: str,
	name: str,
	format=None,
	doc=None,
	no_letterhead=0,
	language=None,
	letterhead=None,
	pdf_generator=None,
):
	"""Download LMS Certificate as a full-bleed A4 landscape PDF (authenticated)."""
	from frappe.utils.print_format import download_pdf as _download_pdf
	from frappe.utils.print_format import validate_print_permission

	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to download the certificate."), frappe.PermissionError)

	if doctype != "LMS Certificate":
		return _download_pdf(
			doctype,
			name,
			format=format,
			doc=doc,
			no_letterhead=no_letterhead,
			language=language,
			letterhead=letterhead,
			pdf_generator=pdf_generator,
		)

	doc = doc or frappe.get_doc(doctype, name)
	if not _can_access_certificate(doc):
		frappe.throw(_("Not permitted to download this certificate."), frappe.PermissionError)
	validate_print_permission(doc)

	from lms.lms.genius_certificate import render_certificate_for_doc

	pdf, _png, learner, _date = render_certificate_for_doc(doc)
	safe_name = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in (learner or "certificate"))
	frappe.local.response.filename = f"Certificate-{safe_name.strip() or name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


def _can_access_certificate(doc) -> bool:
	user = frappe.session.user
	if user == "Guest":
		return False
	if doc.member == user:
		return True
	return _is_certificate_staff(user)


@frappe.whitelist()
def download_certificate_png(name: str):
	"""Download LMS Certificate as a high-resolution PNG."""
	from frappe.utils.print_format import validate_print_permission
	from lms.lms.genius_certificate import render_certificate_for_doc

	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to download the certificate."), frappe.PermissionError)

	doc = frappe.get_doc("LMS Certificate", name)
	if not _can_access_certificate(doc):
		frappe.throw(_("Not permitted to download this certificate."), frappe.PermissionError)
	validate_print_permission(doc)
	_pdf, png, learner, _date = render_certificate_for_doc(doc)
	safe_name = "".join(ch if ch.isalnum() or ch in "-_ " else "" for ch in (learner or "certificate"))
	frappe.local.response.filename = f"Certificate-{safe_name.strip() or name}.png"
	frappe.local.response.filecontent = png
	frappe.local.response.type = "download"
	frappe.local.response.headers = {
		"Content-Type": "image/png",
		"Content-Disposition": f'attachment; filename="Certificate-{safe_name.strip() or name}.png"',
	}


@frappe.whitelist()
def get_certificate_preview(name: str):
	"""Return preview metadata + base64 PNG for the certificate viewer."""
	import base64

	from frappe.utils.print_format import validate_print_permission
	from lms.lms.genius_certificate import render_certificate_for_doc

	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to view the certificate."), frappe.PermissionError)

	doc = frappe.get_doc("LMS Certificate", name)
	if not _can_access_certificate(doc):
		frappe.throw(_("Not permitted to view this certificate."), frappe.PermissionError)
	validate_print_permission(doc)
	_pdf, png, learner, completion_date = render_certificate_for_doc(doc)
	return {
		"name": doc.name,
		"learner_full_name": learner,
		"completion_date": completion_date,
		"course": doc.course,
		"course_title": doc.course_title
		or frappe.db.get_value("LMS Course", doc.course, "title"),
		"template": doc.template or "Genius Certificate Copilot",
		"png_base64": base64.b64encode(png).decode("ascii"),
		"pdf_url": f"/api/method/frappe.utils.print_format.download_pdf?doctype=LMS+Certificate&name={doc.name}&format=Genius%20Certificate%20Copilot",
		"png_url": f"/api/method/lms.lms.doctype.lms_certificate.lms_certificate.download_certificate_png?name={doc.name}",
	}

def get_default_certificate_template():
	# Prefer Genius Copilot template when available
	if frappe.db.exists("Print Format", "Genius Certificate Copilot"):
		return "Genius Certificate Copilot"

	default_certificate_template = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": "LMS Certificate",
			"property": "default_print_format",
		},
		"value",
	)
	if not default_certificate_template:
		default_certificate_template = frappe.db.get_value(
			"Print Format",
			{
				"doc_type": "LMS Certificate",
			},
		)

	return default_certificate_template


def validate_certification_eligibility(course):
	from frappe.utils import flt
	from lms.lms.utils import get_course_progress

	if not frappe.db.exists("LMS Enrollment", {"course": course, "member": frappe.session.user}):
		frappe.throw(_("You are not enrolled in this course."))

	if not frappe.db.get_value("LMS Course", course, "enable_certification"):
		frappe.throw(_("Certification is not enabled for this course."))

	# Recalculate from LMS Course Progress — do not trust forgeable enrollment.progress
	progress = flt(get_course_progress(course, frappe.session.user) or 0)
	if progress < 100:
		frappe.throw(_("You have not completed the course yet."))
	# Sales CRT: certificate is not gated on course feedback.


def issue_certificate_on_completion(course: str, member: str):
	"""Create a certificate after 100% course progress. Feedback is not required."""
	from frappe.utils import flt
	from lms.lms.utils import get_course_progress

	if not course or not member or member in ("Guest",):
		return None

	if not frappe.db.get_value("LMS Course", course, "enable_certification"):
		return None

	if not frappe.db.exists("LMS Enrollment", {"course": course, "member": member}):
		return None

	progress = flt(get_course_progress(course, member) or 0)
	if progress < 100:
		return None

	existing = frappe.db.exists("LMS Certificate", {"member": member, "course": course})
	if existing:
		return frappe.get_doc("LMS Certificate", existing)

	template = get_default_certificate_template()
	certificate = frappe.get_doc(
		{
			"doctype": "LMS Certificate",
			"member": member,
			"course": course,
			"issue_date": nowdate(),
			"template": template,
			"published": 1,
		}
	)
	certificate.flags.ignore_permissions = True
	certificate.insert(ignore_permissions=True)

	enrollment_name = frappe.db.exists(
		"LMS Enrollment", {"course": course, "member": member}
	)
	if enrollment_name:
		frappe.db.set_value(
			"LMS Enrollment",
			enrollment_name,
			"certificate",
			certificate.name,
			update_modified=False,
		)

	return certificate


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	roles = frappe.get_roles(user)
	if (
		"System Manager" in roles
		or "Moderator" in roles
		or "Course Creator" in roles
		or "Batch Evaluator" in roles
	):
		return True
	# Member/owner: view and print only — no write/share via ownership
	if doc.member == user or doc.owner == user:
		return ptype in ("read", "select", "print")
	if ptype in ("read", "select", "print"):
		return bool(doc.published)
	return False


def get_permission_query_conditions(user):
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if (
		"System Manager" in roles
		or "Moderator" in roles
		or "Course Creator" in roles
		or "Batch Evaluator" in roles
	):
		return None
	# Learners see their own certificates plus published directory entries
	return """(`tabLMS Certificate`.member = {user} or `tabLMS Certificate`.published = 1)""".format(
		user=frappe.db.escape(user)
	)
