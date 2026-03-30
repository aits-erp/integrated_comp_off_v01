from unittest import TestCase
from types import SimpleNamespace

import frappe
from frappe.utils import get_datetime

from real_group.helper.attendance_helper import (
    calculate_working_hours_for_attendance,
    get_last_checkout_shift,
    get_specific_multi_checkin_override_fields,
)


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

    def test_specific_multi_checkin_override_uses_last_checkout_shift_and_combined_hours(
        self,
    ):
        logs = [
            frappe._dict(
                log_type="IN",
                shift="B",
                time=get_datetime("2026-03-06 17:41:00"),
                custom_processed_time=get_datetime("2026-03-06 17:41:00"),
            ),
            frappe._dict(
                log_type="OUT",
                shift="B",
                time=get_datetime("2026-03-06 19:41:00"),
                custom_processed_time=get_datetime("2026-03-06 19:41:00"),
            ),
            frappe._dict(
                log_type="IN",
                shift="C",
                time=get_datetime("2026-03-06 22:00:00"),
                custom_processed_time=get_datetime("2026-03-06 22:00:00"),
            ),
            frappe._dict(
                log_type="OUT",
                shift="C",
                time=get_datetime("2026-03-07 06:00:00"),
                custom_processed_time=get_datetime("2026-03-07 06:00:00"),
            ),
        ]
        shift = SimpleNamespace(
            name="C",
            custom_working_hours_threshold_for_present="7:45:00",
            custom_working_hours_threshold_for_half_day="3:50:01",
            custom_working_hours_threshold_for_absent="3:50:00",
        )

        override = get_specific_multi_checkin_override_fields(logs, shift)

        self.assertEqual(get_last_checkout_shift(logs), "C")
        self.assertEqual(override["status"], "Present")
        self.assertEqual(override["shift"], "C")
        self.assertEqual(override["in_time"], get_datetime("2026-03-06 17:41:00"))
        self.assertEqual(override["out_time"], get_datetime("2026-03-07 06:00:00"))
        self.assertEqual(override["working_hours"], 10.0)
        self.assertFalse(override["late_entry"])
        self.assertFalse(override["early_exit"])

    def test_specific_multi_checkin_override_marks_half_day_from_combined_pairs(self):
        logs = [
            frappe._dict(
                log_type="IN",
                shift="G",
                time=get_datetime("2026-03-10 09:00:00"),
                custom_processed_time=get_datetime("2026-03-10 09:00:00"),
            ),
            frappe._dict(
                log_type="OUT",
                shift="G",
                time=get_datetime("2026-03-10 11:00:00"),
                custom_processed_time=get_datetime("2026-03-10 11:00:00"),
            ),
            frappe._dict(
                log_type="IN",
                shift="G",
                time=get_datetime("2026-03-10 13:00:00"),
                custom_processed_time=get_datetime("2026-03-10 13:00:00"),
            ),
            frappe._dict(
                log_type="OUT",
                shift="G",
                time=get_datetime("2026-03-10 18:01:00"),
                custom_processed_time=get_datetime("2026-03-10 18:01:00"),
            ),
        ]
        shift = SimpleNamespace(
            name="G",
            custom_working_hours_threshold_for_present="8:00:00",
            custom_working_hours_threshold_for_half_day="4:00:00",
            custom_working_hours_threshold_for_absent="3:59:59",
        )

        override = get_specific_multi_checkin_override_fields(logs, shift)

        self.assertEqual(override["status"], "Half Day")
        self.assertEqual(override["shift"], "G")
        self.assertEqual(override["in_time"], get_datetime("2026-03-10 09:00:00"))
        self.assertEqual(override["out_time"], get_datetime("2026-03-10 18:01:00"))
        self.assertEqual(override["working_hours"], 7.02)
