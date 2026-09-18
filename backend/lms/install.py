import frappe

from lms.lms.api import give_discussions_permission
from lms.lms.branding import BRAND_NAME


def after_install():
	create_batch_source()
	give_discussions_permission()
	give_user_list_permission()
	give_event_permission()
	set_sales_lms_branding()


def after_sync():
	create_lms_roles()
	set_default_certificate_print_format()
	give_lms_roles_to_admin()
	set_portal_as_default_app()
	set_sales_lms_branding()
	normalize_portal_routes()
	add_team_access_icon()


IL_FAVICON = "/assets/lms/images/il-favicon.png"
IL_LOGO = "/assets/lms/images/il-logo.svg"


def set_sales_lms_branding():
	"""Replace Frappe branding with LMS / Infinity Learn across desk, portal and email."""
	try:
		frappe.db.set_single_value("Website Settings", "app_name", BRAND_NAME)
		frappe.db.set_single_value("Website Settings", "favicon", IL_FAVICON)
		frappe.db.set_single_value("Website Settings", "app_logo", IL_FAVICON)
		frappe.db.set_single_value("Website Settings", "splash_image", IL_FAVICON)
		frappe.db.set_single_value("System Settings", "app_name", BRAND_NAME)
		frappe.db.set_single_value("System Settings", "otp_issuer_name", BRAND_NAME)
		# Drops the "Sent via Frappe" line from every outgoing email.
		frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 1)
		frappe.db.set_single_value("Navbar Settings", "app_logo", IL_FAVICON)

		if frappe.db.exists("Desktop Icon", "Frappe Learning"):
			frappe.db.set_value("Desktop Icon", "Frappe Learning", "label", BRAND_NAME)

		if frappe.db.exists("Workspace", "Learning"):
			frappe.db.set_value("Workspace", "Learning", "label", BRAND_NAME)

		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to set LMS branding: {e}")


def add_team_access_icon():
	"""'Team & Access' tile in the desk's Framework folder, next to Users. Opens the LMS screen."""
	try:
		if not frappe.db.exists("DocType", "Desktop Icon") or frappe.db.exists("Desktop Icon", {"label": "Team & Access"}):
			return
		icon = frappe.get_doc(
			{
				"doctype": "Desktop Icon",
				"label": "Team & Access",
				"icon_type": "Link",
				"link_type": "External",
				"link": "/team",
				"parent_icon": "Framework" if frappe.db.exists("Desktop Icon", "Framework") else None,
				"icon": "users-round",
				"app": "lms",
				"bg_color": "blue",
				"roles": [{"role": "System Manager"}, {"role": "Moderator"}],
			}
		)
		icon.insert(ignore_permissions=True)
		frappe.cache.delete_key("desktop_icons")
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to add Team & Access icon: {e}")


def set_portal_as_default_app():
	frappe.db.set_single_value("System Settings", "default_app", "frappe_lms")


def normalize_portal_routes():
	"""Keep Website Settings / navbar on clean URLs and drop cached /lms redirects."""
	try:
		frappe.db.set_single_value("Website Settings", "home_page", "")
		try:
			frappe.db.set_single_value("Portal Settings", "default_portal_home", "/dashboard")
		except Exception:
			pass
		for source, target in (
			("/lms/courses", "/courses"),
			("/lms/batches", "/batches"),
			("/lms/statistics", "/analytics-dashboard"),
			("/lms/job-openings", "/job-openings"),
			("/lms/dashboard", "/dashboard"),
			("/lms", "/dashboard"),
		):
			link = frappe.db.exists("Top Bar Item", {"url": source})
			if link:
				frappe.db.set_value("Top Bar Item", link, "url", target)
		frappe.clear_cache()
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to normalize portal routes: {e}")


def before_uninstall():
	delete_custom_fields()
	delete_lms_roles()


def create_lms_roles():
	create_course_creator_role()
	create_moderator_role()
	create_evaluator_role()
	create_lms_student_role()
	create_lms_manager_role()


def create_lms_manager_role():
	"""Manager tier: sees and acts on their reporting tree and granted scopes (lms.lms.access)."""
	if frappe.db.exists("Role", "LMS Manager"):
		frappe.db.set_value("Role", "LMS Manager", "desk_access", 0)
	else:
		frappe.get_doc({"doctype": "Role", "role_name": "LMS Manager", "home_page": "", "desk_access": 0}).insert()


def create_course_creator_role():
	if frappe.db.exists("Role", "Course Creator"):
		frappe.db.set_value("Role", "Course Creator", "desk_access", 0)
	else:
		role = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Course Creator",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()


def create_moderator_role():
	if frappe.db.exists("Role", "Moderator"):
		frappe.db.set_value("Role", "Moderator", "desk_access", 0)
	else:
		role = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Moderator",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()


def create_evaluator_role():
	if frappe.db.exists("Role", "Batch Evaluator"):
		frappe.db.set_value("Role", "Batch Evaluator", "desk_access", 0)
	else:
		role = frappe.new_doc("Role")
		role.update(
			{
				"role_name": "Batch Evaluator",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()


def create_lms_student_role():
	if frappe.db.exists("Role", "LMS Student"):
		frappe.db.set_value("Role", "LMS Student", "desk_access", 0)
	else:
		role = frappe.new_doc("Role")
		role.update(
			{
				"role_name": "LMS Student",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()


def set_default_certificate_print_format():
	filters = {
		"doc_type": "LMS Certificate",
		"property": "default_print_format",
	}
	if not frappe.db.exists("Property Setter", filters):
		filters.update(
			{
				"doctype_or_field": "DocType",
				"property_type": "Data",
				"value": "Certificate",
			}
		)

		doc = frappe.new_doc("Property Setter")
		doc.update(filters)
		doc.save()


def delete_custom_fields():
	fields = [
		"user_category",
		"headline",
		"college",
		"city",
		"verify_terms",
		"country",
		"preferred_location",
		"preferred_functions",
		"preferred_industries",
		"work_environment_column",
		"time",
		"role",
		"carrer_preference_details",
		"skill",
		"certification_details",
		"internship",
		"branch",
		"github",
		"medium",
		"linkedin",
		"profession",
		"open_to",
		"cover_image" "work_environment",
		"dream_companies",
		"career_preference_column",
		"attire",
		"collaboration",
		"location_preference",
		"company_type",
		"skill_details",
		"certification",
		"education",
		"work_experience",
		"education_details",
		"hide_private",
		"work_experience_details",
		"profile_complete",
	]

	for field in fields:
		frappe.db.delete("Custom Field", {"fieldname": field})


def create_batch_source():
	sources = [
		"Newsletter",
		"LinkedIn",
		"Twitter",
		"Website",
		"Friend/Colleague/Connection",
		"Google Search",
	]

	for source in sources:
		if not frappe.db.exists("LMS Source", source):
			doc = frappe.new_doc("LMS Source")
			doc.source = source
			doc.save()


def give_lms_roles_to_admin():
	roles = ["Course Creator", "Moderator", "Batch Evaluator"]
	for role in roles:
		if not frappe.db.exists("Has Role", {"parent": "Administrator", "role": role}):
			doc = frappe.new_doc("Has Role")
			doc.parent = "Administrator"
			doc.parenttype = "User"
			doc.parentfield = "roles"
			doc.role = role
			doc.save()


def give_user_list_permission():
	doctype = "User"
	roles = ["Course Creator", "Moderator", "Batch Evaluator"]
	for role in roles:
		permlevel = 0
		create_role(doctype, role, permlevel)
	create_role(doctype, "System Manager", 1)


def give_event_permission():
	doctype = "Event"
	roles = ["Moderator", "Batch Evaluator"]
	for role in roles:
		permlevel = 0
		create_role(doctype, role, permlevel, 1, 1)
	create_role(doctype, "System Manager", 0, 1, 1)


def create_role(doctype, role, permlevel, write=0, create=0):
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel}):
		if not write and not create:
			if role in ["Moderator", "System Manager"]:
				write = 1
			if role == "Moderator":
				create = 1
		doc = frappe.new_doc("Custom DocPerm")
		doc.update(
			{
				"doctype": "Custom DocPerm",
				"parent": doctype,
				"role": role,
				"read": 1,
				"select": 1,
				"write": write,
				"create": create,
				"permlevel": permlevel,
			}
		)
		doc.save()


def delete_lms_roles():
	roles = ["Course Creator", "Moderator", "Batch Evaluator", "LMS Student", "LMS Manager"]
	for role in roles:
		if frappe.db.exists("Role", role):
			frappe.db.delete("Role", role)
