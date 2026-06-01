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
