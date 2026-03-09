import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_year_ending, get_year_start, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.payroll.doctype.salary_slip.test_salary_slip import make_holiday_list

from real_group.patches.fix_cross_day_attendance_request_hours import (
    execute as fix_cross_day_attendance_request_hours,
)


test_dependencies = ["Employee"]


class TestAttendanceRequestOverride(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_name = make_employee(
            "test_cross_day_attendance_request@example.com", company="_Test Company"
        )
        cls.employee = frappe.get_doc("Employee", cls.employee_name)

    def setUp(self):
        frappe.db.delete("Attendance", {"employee": self.employee_name})
        frappe.db.delete("Attendance Request", {"employee": self.employee_name})

        self.holiday_list_name = "RG Attendance Request Test Holiday List"
        if frappe.db.exists("Holiday List", self.holiday_list_name):
            frappe.delete_doc("Holiday List", self.holiday_list_name, force=1)

        self.holiday_list = make_holiday_list(
            list_name=self.holiday_list_name,
            from_date=get_year_start(getdate()),
            to_date=get_year_ending(getdate()),
            add_weekly_offs=False,
        )
        frappe.db.set_value(
            "Employee", self.employee_name, "holiday_list", self.holiday_list
        )

        self.cross_day_shift = self.make_shift(
            shift_name="RG Test Night Shift",
            start_time="22:00:00",
            end_time="06:00:00",
            custom_is_cross_day=1,
        )
        self.day_shift = self.make_shift(
            shift_name="RG Test Day Shift",
            start_time="09:00:00",
            end_time="18:00:00",
            custom_is_cross_day=0,
        )

    def make_shift(self, shift_name: str, **kwargs):
        if frappe.db.exists("Shift Type", shift_name):
            frappe.delete_doc("Shift Type", shift_name, force=1)
        return setup_shift_type(shift_type=shift_name, **kwargs)

    def make_attendance_request(self, **overrides):
        attendance_request = frappe.get_doc(
            {
                "doctype": "Attendance Request",
                "employee": self.employee_name,
                "from_date": getdate(),
                "to_date": getdate(),
                "reason": "On Duty",
                "company": "_Test Company",
                "shift": self.cross_day_shift.name,
                "custom_from_time": "22:00:00",
                "custom_to_time": "06:00:00",
            }
        )
        attendance_request.update(overrides)
        return attendance_request.submit()

    def get_request_attendance(self, attendance_request):
        attendance_name = frappe.db.get_value(
            "Attendance",
            {"attendance_request": attendance_request.name, "docstatus": 1},
            "name",
        )
        return frappe.get_doc("Attendance", attendance_name)

    def test_cross_day_attendance_request_marks_positive_working_hours(self):
        attendance_request = self.make_attendance_request()
        attendance = self.get_request_attendance(attendance_request)

        self.assertEqual(attendance.status, "Present")
        self.assertAlmostEqual(attendance.working_hours, 8.0)

    def test_non_cross_day_request_rejects_reverse_time_window(self):
        with self.assertRaises(frappe.ValidationError):
            self.make_attendance_request(
                shift=self.day_shift.name,
                custom_from_time="18:00:00",
                custom_to_time="09:00:00",
            )

    def test_patch_corrects_existing_negative_cross_day_hours(self):
        attendance_request = self.make_attendance_request()
        attendance = self.get_request_attendance(attendance_request)

        frappe.db.set_value(
            "Attendance",
            attendance.name,
            {"working_hours": -16.0, "custom_working_hours": None},
            update_modified=False,
        )

        fix_cross_day_attendance_request_hours()

        attendance.reload()
        self.assertAlmostEqual(attendance.working_hours, 8.0)
