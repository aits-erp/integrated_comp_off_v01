from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, format_date, get_datetime, get_link_to_form, getdate
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest

from real_group.doc_events.attendance import allocate_c_off, allocate_incentive, update_attendance_tag
from real_group.helper.attendance_helper import (
    create_attendance,
)
from real_group.utils import convert_time_to_hours, is_holiday_for_employee


class AttendanceRequestOverride(AttendanceRequest):
    def create_or_update_attendance(self, date: str):
        attendance_name = self.get_attendance_record(date)
        status = self.get_attendance_status(date)

        if attendance_name:
            # update existing attendance, change the status
            doc = frappe.get_doc("Attendance", attendance_name)
            old_status = doc.status

            if old_status != status:
                # Update working hours by adding existing working hours with new working hours
                self.update_existing_attendance(doc, old_status, status, date)
            else:
                if old_status == "Half Day" and status == "Half Day":
                    status = "Present"
                    self.update_existing_attendance(doc, old_status, status, date)

        else:
            # submit a new attendance record
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.attendance_date = date
            doc.shift = self.shift
            doc.company = self.company
            doc.attendance_request = self.name
            doc.status = status
            # Update working hours
            doc.working_hours = self.get_working_hours()
            doc.insert(ignore_permissions=True)
            doc.submit()

    def update_existing_attendance(self, doc, old_status, status, date):
        working_hours = self.get_working_hours() + (doc.working_hours or 0)
        working_hours_time = self.get_working_hours_time(working_hours)
        doc.db_set(
            {
                "status": status,
                "attendance_request": self.name,
                "working_hours": working_hours,
                "custom_working_hours": working_hours_time,
            }
        )
        text = _("changed the status from {0} to {1} via Attendance Request").format(
            frappe.bold(old_status), frappe.bold(status)
        )
        doc.add_comment(comment_type="Info", text=text)
        self.process_jobs_after_update(doc)
        frappe.msgprint(
            _("Updated status from {0} to {1} for date {2} in the attendance record {3}").format(
                frappe.bold(old_status),
                frappe.bold(status),
                frappe.bold(format_date(date)),
                get_link_to_form("Attendance", doc.name),
            ),
            title=_("Attendance Updated"),
        )

    def process_jobs_after_update(self, doc):
        frappe.enqueue(update_attendance_tag, doc=doc, queue="long", enqueue_after_commit=True)
        frappe.enqueue(allocate_c_off, doc=doc, queue="long", enqueue_after_commit=True)
        frappe.enqueue(allocate_incentive, doc=doc, queue="long", enqueue_after_commit=True)

    def get_working_hours(self):
        from_time = get_datetime(f"{self.from_date} {self.custom_from_time}")
        to_time = get_datetime(f"{self.to_date} {self.custom_to_time}")
        delta = to_time - from_time
        working_hours = convert_time_to_hours(delta)
        return working_hours

    def get_working_hours_time(self, hours: float):
        total_seconds = round(hours * 3600 / 60) * 60
        return timedelta(seconds=total_seconds)

    def should_mark_attendance(self, attendance_date: str) -> bool:
        # 1. Check if attendance_date is a holiday or weekly off
        # 2. If it is holiday and not half day, do not mark attendance
        holiday = is_holiday_for_employee(self.employee, attendance_date)
        if holiday and not holiday.get("is_half_day"):
            frappe.msgprint(
                _("Attendance not submitted for {0} as it is a Holiday.").format(
                    frappe.bold(format_date(attendance_date))
                )
            )
            return False

        # Check if employee is on leave
        if self.has_leave_record(attendance_date):
            frappe.msgprint(
                _("Attendance not submitted for {0} as {1} is on leave.").format(
                    frappe.bold(format_date(attendance_date)), frappe.bold(self.employee)
                )
            )
            return False

        return True

    def has_leave_record(self, attendance_date: str) -> str | None:
        leave = frappe.db.exists(
            "Leave Application",
            {
                "employee": self.employee,
                "docstatus": 1,
                "from_date": ("<=", attendance_date),
                "to_date": (">=", attendance_date),
            },
        )
        if leave:
            leave = frappe.get_doc("Leave Application", leave, for_update=False)
            if leave.half_day and (
                getdate(leave.from_date) == getdate(leave.to_date)
                or getdate(attendance_date) == getdate(leave.half_day_date)
            ):
                return False
        return leave

    @frappe.whitelist()
    def get_attendance_warnings(self) -> list:
        attendance_warnings = []
        request_days = date_diff(self.to_date, self.from_date) + 1

        for day in range(request_days):
            attendance_date = add_days(self.from_date, day)
            # Check if attendance_date is a holiday or weekly off
            if is_holiday_for_employee(self.employee, attendance_date):
                attendance_warnings.append({"date": attendance_date, "reason": "Holiday", "action": "Skip"})
            elif self.has_leave_record(attendance_date):
                attendance_warnings.append({"date": attendance_date, "reason": "On Leave", "action": "Skip"})
            else:
                attendance = self.get_attendance_record(attendance_date)
                if attendance:
                    attendance_warnings.append(
                        {
                            "date": attendance_date,
                            "reason": "Attendance already marked",
                            "record": attendance,
                            "action": "Overwrite",
                        }
                    )

        return attendance_warnings

    # 1. If there is leave application in the attendance then after cancelling attendance, it should be re-created
    # for that leave application. (same goes for half day leave)
    # 2. If attendance is created from the employee checkins, then after cancelling attendance, new attendance should
    # be created from the checkins via. method from attendance_process.
    # 3. If none of the above two conditions are met, then just cancel the attendance as usual and create attendance for
    # Absent.
    def on_cancel(self):
        attendance_list = frappe.get_all(
            "Attendance",
            filters={"employee": self.employee, "attendance_request": self.name, "docstatus": 1},
            fields=["name", "attendance_date", "status"],
        )
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)

        half_day_date = getdate(self.half_day_date) if self.half_day else None
        while from_date <= to_date:
            attendance = next((att for att in attendance_list if getdate(att.attendance_date) == from_date), None)
            has_checkins = (
                frappe.get_all(
                    "Employee Checkin",
                    filters={"attendance": attendance.name},
                    fields=["*"],
                    order_by="time",
                )
                if attendance
                else False
            )
            if attendance:
                frappe.db.set_value("Attendance", attendance.name, "docstatus", 2)

            # CASE 1: For leave
            leave = frappe.db.get_value(
                "Leave Application",
                {
                    "employee": self.employee,
                    "docstatus": 1,
                    "from_date": ("<=", from_date),
                    "to_date": (">=", from_date),
                },
                ["name", "leave_type", "half_day", "half_day_date", "custom_half_type", "from_date", "to_date"],
                as_dict=True,
            )
            if leave and has_checkins:
                self.create_leave_attendance(leave, from_date, half_day_date, has_checkins)
            elif leave and not has_checkins:
                self.create_leave_attendance(leave, from_date, half_day_date, False)

            # CASE 2: For checkins
            elif has_checkins:
                create_attendance(self.employee, from_date, has_checkins)
            else:
                doc = frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": self.employee,
                        "attendance_date": from_date,
                        "status": "Absent",
                        "company": self.company,
                    }
                ).insert(ignore_permissions=True)
                doc.submit()
            from_date = add_days(from_date, 1)

    def create_leave_attendance(self, leave, from_date, half_day_date, has_checkins):
        if leave.half_day:
            if getdate(leave.from_date) == getdate(leave.to_date) or (
                half_day_date and getdate(half_day_date) == from_date
            ):
                doc = frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": self.employee,
                        "attendance_date": from_date,
                        "status": "Half Day",
                        "custom_half_type": leave.custom_half_type,
                        "company": self.company,
                        "leave_application": leave.name,
                        "leave_type": leave.leave_type,
                    }
                ).insert(ignore_permissions=True)
                doc.submit()
                if has_checkins:
                    # Now process the checkins to create attendance for present half day
                    create_attendance(from_date, self.employee, has_checkins)
        else:
            doc = frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "employee": self.employee,
                    "attendance_date": from_date,
                    "status": "On Leave",
                    "company": self.company,
                    "leave_application": leave.name,
                    "leave_type": leave.leave_type,
                }
            ).insert(ignore_permissions=True)
            doc.submit()
