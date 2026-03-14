from datetime import timedelta
from types import SimpleNamespace
from unittest import TestCase

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
