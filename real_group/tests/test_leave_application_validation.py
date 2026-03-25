from datetime import date
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


leave_application = import_module("real_group.doc_events.leave_application")


class TestLeaveApplicationValidation(TestCase):
    def test_validate_el_and_cl_allows_earned_leave_with_opposite_half_comp_off(self):
        doc = SimpleNamespace(
            leave_type="Earned Leave - Plant",
            employee="230011",
            name="LAP-NEW",
            from_date=date(2026, 3, 5),
            to_date=date(2026, 3, 5),
            half_day=1,
            half_day_date=date(2026, 3, 5),
        )
        existing = SimpleNamespace(
            name="LAP-CO",
            leave_type="Compensatory Off",
            from_date=date(2026, 3, 5),
            to_date=date(2026, 3, 5),
            half_day=1,
            half_day_date=date(2026, 3, 5),
        )

        with patch.object(leave_application.frappe, "get_all", return_value=[existing]):
            leave_application.validate_el_and_cl(doc)

    def test_validate_el_and_cl_allows_casual_leave_with_opposite_half_lwp(self):
        doc = SimpleNamespace(
            leave_type="Casual Leave - Plant",
            employee="230011",
            name="LAP-NEW",
            from_date=date(2026, 3, 5),
            to_date=date(2026, 3, 5),
            half_day=1,
            half_day_date=date(2026, 3, 5),
        )
        existing = SimpleNamespace(
            name="LAP-LWP",
            leave_type="Leave Without Pay",
            from_date=date(2026, 3, 5),
            to_date=date(2026, 3, 5),
            half_day=1,
            half_day_date=date(2026, 3, 5),
        )

        with patch.object(leave_application.frappe, "get_all", return_value=[existing]):
            leave_application.validate_el_and_cl(doc)
