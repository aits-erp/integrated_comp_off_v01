from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


attendance_request = import_module("real_group.doc_events.attendace_request")


class TestAttendanceRequestValidation(TestCase):
    def test_rejected_request_requires_reason(self):
        doc = SimpleNamespace(
            workflow_state="Rejected by HOD",
            custom_reason_for_rejection="",
        )

        with patch.object(attendance_request.frappe, "_", side_effect=lambda message: message):
            with patch.object(attendance_request.frappe, "throw", side_effect=Exception) as throw:
                with self.assertRaises(Exception):
                    attendance_request.validate_workflow_state(doc)

        throw.assert_called_once_with("Kindly set the reason for rejection")

    def test_rejected_request_allows_reason(self):
        doc = SimpleNamespace(
            workflow_state="Rejected by HR",
            custom_reason_for_rejection="Not applicable",
        )

        with patch.object(attendance_request.frappe, "throw") as throw:
            attendance_request.validate_workflow_state(doc)

        throw.assert_not_called()

    def test_non_rejected_request_does_not_require_reason(self):
        doc = SimpleNamespace(
            workflow_state="Pending at HR",
            custom_reason_for_rejection="",
        )

        with patch.object(attendance_request.frappe, "throw") as throw:
            attendance_request.validate_workflow_state(doc)

        throw.assert_not_called()

    def test_mis_punch_limit_zero_allows_unlimited_requests(self):
        doc = SimpleNamespace(employee="EMP-001", from_date="2026-06-06", name="HR-ARQ-001")

        with patch.object(attendance_request, "get_allowed_mis_punch_days", return_value=0):
            with patch.object(attendance_request, "get_monthly_mis_punch_request_count") as count:
                with patch.object(attendance_request.frappe, "throw") as throw:
                    attendance_request.validate_mis_punch_monthly_limit(doc)

        count.assert_not_called()
        throw.assert_not_called()

    def test_mis_punch_limit_allows_request_when_count_is_below_limit(self):
        doc = SimpleNamespace(employee="EMP-001", from_date="2026-06-06", name="HR-ARQ-001")

        with patch.object(attendance_request, "get_allowed_mis_punch_days", return_value=3):
            with patch.object(attendance_request, "get_monthly_mis_punch_request_count", return_value=2):
                with patch.object(attendance_request.frappe, "throw") as throw:
                    attendance_request.validate_mis_punch_monthly_limit(doc)

        throw.assert_not_called()

    def test_mis_punch_limit_rejects_request_when_count_reaches_limit(self):
        doc = SimpleNamespace(employee="EMP-001", from_date="2026-06-06", name="HR-ARQ-001")

        with patch.object(attendance_request, "get_allowed_mis_punch_days", return_value=3):
            with patch.object(attendance_request, "get_monthly_mis_punch_request_count", return_value=3):
                with patch.object(attendance_request.frappe, "_", side_effect=lambda message: message):
                    with patch.object(attendance_request.frappe, "throw", side_effect=Exception) as throw:
                        with self.assertRaises(Exception):
                            attendance_request.validate_mis_punch_monthly_limit(doc)

        throw.assert_called_once_with(attendance_request.MIS_PUNCH_LIMIT_REACHED_MESSAGE)

    def test_mis_punch_rejects_request_when_valid_checkin_pair_exists(self):
        doc = SimpleNamespace(employee="EMP-001", from_date="2026-06-06")
        checkins = [
            SimpleNamespace(log_type="IN", time="2026-06-06 09:00:00"),
            SimpleNamespace(log_type="OUT", time="2026-06-06 18:00:00"),
        ]

        with patch.object(attendance_request, "get_mis_punch_checkins", return_value=checkins):
            with patch.object(attendance_request.frappe, "_", side_effect=lambda message: message):
                with patch.object(attendance_request.frappe, "throw", side_effect=Exception) as throw:
                    with self.assertRaises(Exception):
                        attendance_request.validate_mis_punch_checkin_pair(doc)

        throw.assert_called_once_with(attendance_request.MIS_PUNCH_VALID_PAIR_EXISTS_MESSAGE)

    def test_mis_punch_allows_request_when_checkout_is_missing(self):
        doc = SimpleNamespace(employee="EMP-001", from_date="2026-06-06")
        checkins = [SimpleNamespace(log_type="IN", time="2026-06-06 09:00:00")]

        with patch.object(attendance_request, "get_mis_punch_checkins", return_value=checkins):
            with patch.object(attendance_request.frappe, "throw") as throw:
                attendance_request.validate_mis_punch_checkin_pair(doc)

        throw.assert_not_called()

    def test_mis_punch_does_not_treat_out_before_in_as_valid_pair(self):
        checkins = [
            SimpleNamespace(log_type="OUT", time="2026-06-06 08:00:00"),
            SimpleNamespace(log_type="IN", time="2026-06-06 09:00:00"),
        ]

        with patch.object(attendance_request, "get_mis_punch_checkins", return_value=checkins):
            has_valid_pair = attendance_request.has_valid_mis_punch_checkin_pair(
                "EMP-001", "2026-06-06"
            )

        self.assertFalse(has_valid_pair)
