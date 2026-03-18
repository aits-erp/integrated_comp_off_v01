from datetime import date, datetime
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


day_wise_attendance = import_module(
    "real_group.real_group.report.[new]_day_wise_attendance.[new]_day_wise_attendance"
)
month_wise_attendance = import_module(
    "real_group.real_group.report.[new]_month_wise_attendance.[new]_month_wise_attendance"
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

    @patch.object(day_wise_attendance.frappe, "get_all")
    def test_day_wise_get_employees_excludes_records_outside_report_month(self, mock_get_all):
        mock_get_all.return_value = [
            {"name": "12500", "date_of_joining": date(2026, 1, 15), "relieving_date": None},
            {"name": "12501", "date_of_joining": date(2025, 1, 1), "relieving_date": date(2026, 1, 15)},
            {"name": "12799", "date_of_joining": date(2025, 1, 1), "relieving_date": date(2025, 12, 31)},
            {"name": "12800", "date_of_joining": date(2026, 2, 1), "relieving_date": None},
        ]

        employees = day_wise_attendance.get_employees(
            company="Real Ispat and Power Ltd",
            branch="Plant Site",
            division=None,
            department=None,
            employee=None,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

        self.assertEqual([employee["name"] for employee in employees], ["12500", "12501"])

    @patch.object(month_wise_attendance.frappe, "get_all")
    def test_month_wise_get_employees_returns_no_rows_for_future_joining_employee(self, mock_get_all):
        mock_get_all.return_value = [
            {"name": "12800", "date_of_joining": date(2026, 2, 1), "relieving_date": None}
        ]

        employees = month_wise_attendance.get_employees(
            company="Real Ispat and Power Ltd",
            branch="Plant Site",
            division=None,
            department=None,
            employee="12800",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            all_company=False,
        )

        self.assertEqual(employees, [])

    def test_top_row_status_totals_include_new_holiday_weekly_off_leave_and_od_counts(self):
        totals = day_wise_attendance.init_top_row_status_totals()

        for status_code in ["HO", "WO", "HEL", "ODCL", "POW", "POD", "CLCO", "PHO"]:
            day_wise_attendance.add_top_row_status_totals(totals, status_code)

        self.assertEqual(
            totals,
            {
                "holiday": 1.5,
                "weekly_off": 2.0,
                "leaves": 2.0,
                "od": 1.0,
            },
        )

    def test_holiday_extra_work_returns_empty_when_checkins_are_missing(self):
        self.assertEqual(day_wise_attendance.get_holiday_extra_work([]), "")

    def test_holiday_extra_work_uses_first_and_last_checkin_when_available(self):
        checkins = [
            {"time": datetime(2026, 3, 11, 7, 56, 26)},
            {"time": datetime(2026, 3, 11, 20, 2, 30)},
        ]

        self.assertEqual(day_wise_attendance.get_holiday_extra_work(checkins), "12:06")
