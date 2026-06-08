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
