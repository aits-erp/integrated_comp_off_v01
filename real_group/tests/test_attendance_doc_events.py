from datetime import timedelta
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from real_group.doc_events import attendance as attendance_doc_events
from real_group.doc_events.attendance import validate


class TestAttendanceDocEvents(TestCase):
    def test_validate_keeps_sub_day_custom_working_hours(self):
        doc = SimpleNamespace(working_hours=8.5, custom_working_hours=None)

        validate(doc)

        self.assertEqual(doc.custom_working_hours, timedelta(hours=8, minutes=30))

    def test_validate_skips_custom_working_hours_for_24h_plus(self):
        doc = SimpleNamespace(working_hours=24.02, custom_working_hours=None)

        validate(doc)

        self.assertIsNone(doc.custom_working_hours)

    def test_has_valid_holiday_in_out_pair_uses_same_day_unlinked_checkins(self):
        doc = SimpleNamespace(name="HR-ATT-TEST-1", employee="10794", attendance_date=date(2026, 2, 16))

        with patch.object(
            attendance_doc_events.frappe,
            "get_all",
            side_effect=[[], ["IN", "OUT"]],
        ):
            self.assertTrue(attendance_doc_events.has_valid_holiday_in_out_pair(doc))
