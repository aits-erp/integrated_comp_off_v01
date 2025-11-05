from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, format_date, get_datetime, get_link_to_form, getdate
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest

from real_group.doc_events.attendance import allocate_c_off, allocate_incentive, update_attendance_tag
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
        update_attendance_tag(doc)
        allocate_c_off(doc)
        allocate_incentive(doc)
        frappe.msgprint(
            _("Updated status from {0} to {1} for date {2} in the attendance record {3}").format(
                frappe.bold(old_status),
                frappe.bold(status),
                frappe.bold(format_date(date)),
                get_link_to_form("Attendance", doc.name),
            ),
            title=_("Attendance Updated"),
        )

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
        # Check if attendance_date is a holiday or weekly off
        if is_holiday_for_employee(self.employee, attendance_date):
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

    # TODO: Add override for on_cancel here
    # 1. If there is leave application in the attendance then after cancelling attendance, it should be re-created
    # for that leave application. (same goes for half day leave)
    # 2. If attendance is created from the employee checkins, then after cancelling attendance, new attendance should
    # be created from the checkins via. method from attendance_process.
    # 3. If none of the above two conditions are met, then just cancel the attendance as usual and create attendance for
    # Absent.
