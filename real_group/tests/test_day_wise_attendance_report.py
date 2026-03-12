from datetime import date
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


day_wise_attendance = import_module(
    "real_group.real_group.report.[new]_day_wise_attendance.[new]_day_wise_attendance"
)


def get_leave_type_doc(name):
    if name == "Compensatory Off":
        return SimpleNamespace(is_earned_leave=False, is_compensatory=True, is_lwp=False, name=name)
    if name == "Earned Leave - Plant":
        return SimpleNamespace(is_earned_leave=True, is_compensatory=False, is_lwp=False, name=name)
    if name == "Casual Leave - Plant":
        return SimpleNamespace(is_earned_leave=False, is_compensatory=False, is_lwp=False, name=name)
    raise AssertionError(f"Unexpected leave type requested in test: {name}")


class TestDayWiseAttendanceReport(TestCase):
    def setUp(self):
        self.target_date = date(2026, 1, 4)
        self.primary_application = SimpleNamespace(
            name="AP-LAP-PRIMARY",
            half_day=1,
            half_day_date=self.target_date,
            custom_half_type="Second Half",
        )
        self.primary_comp_off = get_leave_type_doc("Compensatory Off")

    def test_half_day_combo_ignores_rejected_earned_leave_with_approved_comp_off(self):
        other_leave = {
            "name": "AP-LAP-REJECTED-EL",
            "leave_type": "Earned Leave - Plant",
            "status": "Rejected",
            "docstatus": 0,
            "custom_half_type": "Second Half",
        }

        with patch.object(day_wise_attendance.frappe, "get_all", return_value=[other_leave]):
            result = day_wise_attendance.get_half_day_combo_status(
                "50010", self.target_date, self.primary_application, self.primary_comp_off
            )

        self.assertIsNone(result)

    def test_half_day_combo_ignores_rejected_casual_leave_with_approved_comp_off(self):
        other_leave = {
            "name": "AP-LAP-REJECTED-CL",
            "leave_type": "Casual Leave - Plant",
            "status": "Rejected",
            "docstatus": 0,
            "custom_half_type": "First Half",
        }

        with patch.object(day_wise_attendance.frappe, "get_all", return_value=[other_leave]):
            result = day_wise_attendance.get_half_day_combo_status(
                "50010", self.target_date, self.primary_application, self.primary_comp_off
            )

        self.assertIsNone(result)

    def test_half_day_combo_keeps_approved_earned_leave_with_approved_comp_off(self):
        other_leave = SimpleNamespace(
            name="AP-LAP-APPROVED-EL",
            leave_type="Earned Leave - Plant",
            status="Approved",
            docstatus=1,
            custom_half_type="First Half",
        )

        with patch.object(day_wise_attendance.frappe, "get_all", return_value=[other_leave]):
            with patch.object(
                day_wise_attendance.frappe,
                "get_cached_doc",
                side_effect=lambda _doctype, name: get_leave_type_doc(name),
            ):
                result = day_wise_attendance.get_half_day_combo_status(
                    "50010", self.target_date, self.primary_application, self.primary_comp_off
                )

        self.assertEqual(result, "ELCO")
