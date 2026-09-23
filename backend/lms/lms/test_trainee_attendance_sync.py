import frappe
from frappe.tests import UnitTestCase

from lms.lms.trainee_attendance_sync import sync_from_live_class_participant


class TestTraineeAttendanceSync(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.email = f"zoom-crt-{frappe.generate_hash(length=6)}@example.com"
		self.trainee = frappe.get_doc(
			{
				"doctype": "Sales Trainee",
				"trainee_name": "Zoom Synced Trainee",
				"personal_email": self.email,
				"date_of_joining": "2026-10-06",
			}
		).insert(ignore_permissions=True)

	def test_matching_participant_creates_zoom_sourced_attendance(self):
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": self.email,
				"joined_at": "2026-10-06 09:00:00",
				"left_at": "2026-10-06 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_links = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")
		row = frappe.db.get_value(
			"Sales Trainee Attendance",
			{"trainee": self.trainee.name, "attendance_date": "2026-10-06"},
			["status", "source"],
			as_dict=True,
		)
		self.assertIsNotNone(row)
		self.assertEqual(row.status, "Present")
		self.assertEqual(row.source, "Zoom Sync")

	def test_non_matching_participant_is_a_no_op(self):
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": "not-a-trainee@example.com",
				"joined_at": "2026-10-06 09:00:00",
				"left_at": "2026-10-06 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_links = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")  # must not raise
		count = frappe.db.count(
			"Sales Trainee Attendance", {"attendance_date": "2026-10-06", "trainee": self.trainee.name}
		)
		self.assertEqual(count, 0)

	def test_existing_manual_entry_for_same_day_is_not_overwritten(self):
		from lms.lms.doctype.sales_trainee_attendance.sales_trainee_attendance import mark

		mark(self.trainee.name, "2026-10-07", "Absent", source="Manual")
		participant = frappe.get_doc(
			{
				"doctype": "LMS Live Class Participant",
				"live_class": "does-not-need-to-exist-for-this-test",
				"member": self.email,
				"joined_at": "2026-10-07 09:00:00",
				"left_at": "2026-10-07 10:00:00",
				"duration": 60,
			}
		)
		participant.flags.ignore_links = True
		participant.insert(ignore_permissions=True)
		sync_from_live_class_participant(participant, "after_insert")
		status = frappe.db.get_value(
			"Sales Trainee Attendance", {"trainee": self.trainee.name, "attendance_date": "2026-10-07"}, "status"
		)
		self.assertEqual(status, "Absent")  # manual entry wins; Zoom sync does not clobber a correction
