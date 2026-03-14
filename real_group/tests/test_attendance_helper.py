from unittest import TestCase

import frappe
from frappe.utils import get_datetime

from real_group.helper.attendance_helper import calculate_working_hours_for_attendance


class TestAttendanceHelper(TestCase):
    def test_negative_processed_hours_fall_back_to_original_checkin_time(self):
        logs = [
            frappe._dict(
                log_type="IN",
                time=get_datetime("2026-03-10 08:09:15"),
                custom_processed_time=get_datetime("2026-03-10 08:30:00"),
            ),
            frappe._dict(
                log_type="OUT",
                time=get_datetime("2026-03-10 08:09:19"),
                custom_processed_time=get_datetime("2026-03-10 08:09:19"),
            ),
        ]

        working_hours, in_time, out_time = calculate_working_hours_for_attendance(logs)

        self.assertEqual(working_hours, 0.0)
        self.assertEqual(in_time, get_datetime("2026-03-10 08:09:15"))
        self.assertEqual(out_time, get_datetime("2026-03-10 08:09:19"))

    def test_original_checkin_time_is_not_used_when_processed_hours_are_positive(self):
        logs = [
            frappe._dict(
                log_type="IN",
                time=get_datetime("2026-03-10 08:00:00"),
                custom_processed_time=get_datetime("2026-03-10 09:00:00"),
            ),
            frappe._dict(
                log_type="OUT",
                time=get_datetime("2026-03-10 17:00:00"),
                custom_processed_time=get_datetime("2026-03-10 17:00:00"),
            ),
        ]

        working_hours, in_time, out_time = calculate_working_hours_for_attendance(logs)

        self.assertEqual(working_hours, 8.0)
        self.assertEqual(in_time, get_datetime("2026-03-10 09:00:00"))
        self.assertEqual(out_time, get_datetime("2026-03-10 17:00:00"))
