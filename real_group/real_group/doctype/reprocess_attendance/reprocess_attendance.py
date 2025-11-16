# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, get_link_to_form, getdate

from real_group.tasks.process_attendance import process as _process_attendance
from real_group.utils import is_holiday_for_employee


class ReprocessAttendance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        branch: DF.Link
        company: DF.Link
        department: DF.Link | None
        division: DF.Link | None
        employee: DF.Link
        from_date: DF.Date
        reprocess_attendance_bulk: DF.Link | None
        status: DF.Literal["Draft", "In Progress", "Completed", "Error"]
        to_date: DF.Date
    # end: auto-generated types

    def validate(self):
        self.validate_dates()
        self.validate_salary_slip(*self.get_dates())

    def before_submit(self):
        from_date, to_date = self.get_dates()
        self.validate_salary_slip(from_date, to_date)

    def on_submit(self):
        self.process_removal()
        self.reprocess()

    def get_leave_applications(self, from_date, to_date):
        leave_applications = frappe.get_all(
            "Leave Application",
            filters={
                "employee": self.employee,
                "from_date": ["between", [from_date, to_date]],
                "to_date": ["between", [from_date, to_date]],
                "docstatus": 1,
            },
            pluck="name",
        )
        return leave_applications

    def get_requests(self, from_date, to_date):
        attendance_requests = frappe.get_all(
            "Attendance Request",
            filters={
                "employee": self.employee,
                "from_date": ["between", [from_date, to_date]],
                "to_date": ["between", [from_date, to_date]],
                "docstatus": 1,
            },
            pluck="name",
        )
        return attendance_requests

    def validate_dates(self):
        from_date, to_date = self.get_dates()
        if from_date > to_date:
            frappe.throw(frappe._("From Date cannot be greater than To Date"))
        if to_date > getdate():
            frappe.throw(frappe._("To Date cannot be greater than today's date"))

    def get_dates(self):
        return getdate(self.from_date), getdate(self.to_date)

    def validate_salary_slip(self, from_date, to_date):
        salary_exists = frappe.db.exists(
            "Salary Slip",
            {
                "employee": self.employee,
                "start_date": ["<=", from_date],
                "end_date": [">=", to_date],
                "docstatus": ["!=", 2],
            },
        )
        if salary_exists:
            frappe.throw(
                frappe._("Salary Slip(s) exist for the selected period: {0}").format(
                    get_link_to_form("Salary Slip", salary_exists)
                )
            )

    def get_link_to_self(self):
        return get_link_to_form("Reprocess Attendance", self.name)

    def process_removal(self):
        from_date, to_date = self.get_dates()
        self.cancel_attendance(from_date, to_date)
        frappe.db.commit()  # nosemgrep

    def reprocess(self):
        from_date, to_date = self.get_dates()
        employee_grade = frappe.db.get_value("Employee", self.employee, "grade")
        grade = frappe.get_doc("Employee Grade", employee_grade, for_update=False)
        if grade.custom_no_punch_applicable:
            self.process_for_no_checkins(from_date, to_date)
        elif grade.custom_single_punch_applicable:
            self.process_single_checkins(from_date, to_date)
        else:
            self.process_attendance(from_date, to_date)

    def process_for_no_checkins(self, from_date, to_date):
        start_date = from_date
        if getdate(to_date) > getdate():
            end_date = getdate()
        else:
            end_date = getdate(to_date)

        while start_date <= add_days(end_date, 1):
            attendance = frappe.get_doc(
                {
                    "naming_series": "HR-ATT-.YYYY.-",
                    "doctype": "Attendance",
                    "employee": self.employee,
                    "status": "Present",
                    "attendance_date": start_date,
                    "company": self.company,
                    "custom_reprocess_reference": self.name,
                    "custom_attendance_tag": "P",
                }
            )
            attendance.save()
            attendance.add_tag("No Check in Required")
            attendance.submit()
            frappe.db.commit()  # nosemgrep
            start_date = add_days(start_date, 1)

    def process_single_checkins(self, from_date, to_date):
        start_date = from_date
        end_date = to_date

        while start_date <= add_days(end_date, 1):
            start_time = get_datetime(add_days(start_date, -1))
            end_time = get_datetime(add_days(start_date, 1))
            holiday = is_holiday_for_employee(self.employee, start_date)
            filters = [
                ["employee", "=", self.employee],
                ["shift_start", ">=", start_time],
                ["shift_end", "<", end_time],
            ]
            emp_checkin = frappe.db.count("Employee Checkin", filters)
            if holiday:
                attendance = frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": self.employee,
                        "attendance_date": start_date,
                        "status": "Present",
                        "custom_attendance_tag": "HO" if not holiday.get("is_weekly_off") else "WO",
                        "custom_reprocess_reference": self.name,
                    }
                )
                attendance.insert(ignore_permissions=True)
                attendance.submit()
            elif holiday and emp_checkin and emp_checkin > 0:
                attendance = frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": self.employee,
                        "attendance_date": start_date,
                        "status": "Present",
                        "custom_attendance_tag": "POH",
                        "custom_reprocess_reference": self.name,
                    }
                )
                attendance.insert(ignore_permissions=True)
                attendance.submit()
            else:
                if not emp_checkin or emp_checkin == 0:
                    attendance = frappe.get_doc(
                        {
                            "doctype": "Attendance",
                            "employee": self.employee,
                            "attendance_date": start_date,
                            "status": "Absent",
                            "custom_attendance_tag": "A",
                            "custom_reprocess_reference": self.name,
                        }
                    )
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()

                else:
                    checkins = frappe.get_all("Employee Checkin", filters=filters, pluck="name")
                    shift_date = getdate(checkins[0].get("shift_start"))
                    attendance = frappe.get_doc(
                        {
                            "doctype": "Attendance",
                            "employee": self.employee,
                            "attendance_date": shift_date,
                            "status": "Present",
                            "custom_attendance_tag": "P",
                            "custom_reprocess_reference": self.name,
                        }
                    )
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()
                    for checkin in checkins:
                        frappe.db.set_value("Employee Checkin", checkin, "attendance", attendance.name)
            attendance.add_tag("Single Check in Required")
            frappe.db.commit()  # nosemgrep
            start_date = add_days(start_date, 1)

    def process_attendance(self, from_date, to_date):
        start_date = from_date
        end_date = to_date

        while start_date <= add_days(end_date, 1):
            try:
                _process_attendance(from_date=start_date, employee_names=[self.employee], reprocess_ref=self.name)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(), f"Error in Reprocess Attendance: {self.name} for date {start_date}"
                )
            start_date = add_days(start_date, 1)

        self.apply_leave_applications(from_date, to_date)
        self.apply_attendance_requests(from_date, to_date)

    def apply_attendance_requests(self, from_date, to_date):
        requests = self.get_requests(from_date, to_date)
        for request in requests:
            try:
                doc = frappe.get_doc("Attendance Request", request)
                doc.create_attendance_records()
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Error in Reprocess Attendance while applying Attendance Request: {request} for Reprocess Attendance: {self.name}",
                )

    def apply_leave_applications(self, from_date, to_date):
        leave_applications = self.get_leave_applications(from_date, to_date)
        for application in leave_applications:
            try:
                doc = frappe.get_doc("Leave Application", application)
                doc.update_attendance()
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Error in Reprocess Attendance while applying Leave Application: {application} for Reprocess Attendance: {self.name}",
                )

    def cancel_attendance(self, from_date=None, to_date=None):
        attendances = frappe.get_all(
            "Attendance",
            filters={"employee": self.employee, "attendance_date": ["between", [from_date, to_date]], "docstatus": 1},
            pluck="name",
        )

        for attendance in attendances:
            doc = frappe.get_doc("Attendance", attendance)
            doc.cancel()
            doc.add_comment(
                comment_type="Comment",
                text=frappe._("Cancelled by Reprocess Attendance {0}".format(self.get_link_to_self())),
            )
