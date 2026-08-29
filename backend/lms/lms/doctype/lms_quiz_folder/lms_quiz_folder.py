import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.utils import generate_slug


class LMSQuizFolder(Document):
	def autoname(self):
		if not self.name:
			self.name = generate_slug(self.title, "LMS Quiz Folder")

	def on_trash(self):
		has_subfolders = frappe.db.exists("LMS Quiz Folder", {"parent_quiz_folder": self.name})
		if has_subfolders:
			frappe.throw(_("Cannot delete folder that contains subfolders. Delete subfolders first."))

		has_quizzes = frappe.db.exists("LMS Quiz", {"quiz_folder": self.name})
		if has_quizzes:
			frappe.throw(_("Cannot delete folder that contains quizzes. Move or delete quizzes first."))
