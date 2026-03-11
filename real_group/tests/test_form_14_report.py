from datetime import datetime
from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase


form_14 = import_module("real_group.real_group.report.[new]_form_14.[new]_form_14")


class TestForm14Report(TestCase):
    def test_processed_half_day_leave_without_half_type_uses_presence_side(self):
        checkins = [SimpleNamespace(time=datetime(2026, 1, 8, 14, 5, 26))]

        result = form_14.map_status_to_halves("PEL", "HEL", checkins, 4.34, False, None)

        self.assertEqual(result, ("EL", "P"))

    def test_half_day_leave_without_half_type_handles_first_half_presence(self):
        checkins = [SimpleNamespace(time=datetime(2026, 1, 8, 9, 0, 0))]

        result = form_14.map_status_to_halves("PCL", "HCL", checkins, 4.0, False, None)

        self.assertEqual(result, ("P", "CL"))

    def test_optional_leave_half_without_half_type_does_not_crash(self):
        checkins = [SimpleNamespace(time=datetime(2026, 1, 26, 9, 0, 0))]

        result = form_14.map_status_to_halves("ELHO", "ELHO", checkins, 4.0, {"is_holiday": 1}, None)

        self.assertEqual(result, ("P", "EL"))

    def test_rebalance_presence_halves_handles_empty_pair(self):
        self.assertEqual(form_14.rebalance_presence_halves(None, False), ("", ""))
