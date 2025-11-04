import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from frappe import _
from frappe.utils import add_days, format_date, getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import update_attendance_in_checkins
from hrms.hr.doctype.leave_application.leave_application import (
    AttendanceAlreadyMarkedError,
    InsufficientLeaveBalanceError,
    LeaveApplication,
    get_leave_balance_on,
    get_number_of_leave_days,
    is_lwp,
)

from real_group.doc_events.attendance import update_attendance_tag
from real_group.tasks.process_attendance import (
    get_attendance,
    mark_attendance_and_link_log,
    mark_half_day_based_on_deduction_cycle,
    update_time,
)
from real_group.utils import get_actual_leave_balance_cf, get_holiday_dates_for_employee, is_holiday_for_employee


class LeaveApplicationOverride(LeaveApplication):
    def update_attendance(self):
        if self.status != "Approved":
            return

        grade = frappe.get_value("Employee", self.employee, "grade")
        apply_sandwich = frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag")

        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)

        # Fetch all dates in range
        all_dates = [d for d in daterange(from_date, to_date)]

        # Preload holiday info
        holiday_map = {d: bool((is_holiday_for_employee(self.employee, d) or {}).get("is_holiday")) for d in all_dates}

        # Determine leave/holiday status for each date
        status = {}
        for d in all_dates:
            if self.half_day and getdate(self.half_day_date) == d:
                status[d] = "half"
            elif holiday_map[d]:
                status[d] = "holiday"
            else:
                status[d] = "full"

        # --- Sandwich logic ---
        # Only if sandwich flag is True, include holidays between two full leaves
        if apply_sandwich:
            i = 0
            n = len(all_dates)
            while i < n:
                d = all_dates[i]
                if status[d] == "holiday":
                    block_start = i
                    while i < n and status[all_dates[i]] == "holiday":
                        i += 1
                    block_end = i - 1

                    prev_d = add_days(all_dates[block_start], -1)
                    next_d = add_days(all_dates[block_end], 1)

                    prev_is_full = prev_d in status and status[prev_d] == "full"
                    next_is_full = next_d in status and status[next_d] == "full"

                    # Only count if both adjacent are full leave days
                    if prev_is_full and next_is_full:
                        for j in range(block_start, block_end + 1):
                            status[all_dates[j]] = "full"
                else:
                    i += 1
        else:
            # Sandwich not applied — exclude all holidays from attendance update
            holiday_dates = get_holiday_dates_for_employee(self.employee, self.from_date, self.to_date)
            all_dates = [d for d in all_dates if d.strftime("%Y-%m-%d") not in holiday_dates]

        # --- Now mark attendance ---
        for d in all_dates:
            date = d.strftime("%Y-%m-%d")
            attendance_name = frappe.db.exists(
                "Attendance", dict(employee=self.employee, attendance_date=date, docstatus=("!=", 2))
            )

            # Skip excluded holidays (non-sandwich)
            if status[d] == "holiday":
                if attendance_name:
                    attendance = frappe.get_doc("Attendance", attendance_name)
                    attendance.flags.ignore_permissions = True
                    if attendance.docstatus == 1:
                        attendance.cancel()
                continue

            # Create or update attendance
            self.create_or_update_attendance(attendance_name, date)

    def create_or_update_attendance(self, attendance_name, date):
        status = "Half Day" if self.half_day_date and getdate(date) == getdate(self.half_day_date) else "On Leave"

        if attendance_name:
            # update existing attendance, change absent to on leave
            doc = frappe.get_doc("Attendance", attendance_name)
            doc.db_set(
                {
                    "status": status,
                    "leave_type": self.leave_type,
                    "leave_application": self.name,
                    "custom_half_type": self.custom_half_type,
                }
            )
            update_attendance_tag(doc)
        else:
            # make new attendance and submit it
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.employee_name = self.employee_name
            doc.attendance_date = date
            doc.company = self.company
            doc.leave_type = self.leave_type
            doc.leave_application = self.name
            doc.status = status
            doc.custom_half_type = self.custom_half_type
            doc.flags.ignore_validate = True
            doc.insert(ignore_permissions=True)
            doc.submit()

    def cancel_attendance(self):
        if self.docstatus != 2:
            return

        from frappe.utils import add_days, getdate

        Attendance = frappe.qb.DocType("Attendance")

        # Fetch all attendance records linked to this leave application
        result = (
            frappe.qb.from_(Attendance)
            .select(Attendance.name, Attendance.attendance_date)
            .where(
                (Attendance.employee == self.employee)
                & (Attendance.attendance_date.between(self.from_date, self.to_date))
                & (Attendance.docstatus < 2)
                & ((Attendance.status.isin(["On Leave", "Half Day"])) | (Attendance.leave_application == self.name))
            )
            .run(as_dict=True)
        )

        if not result:
            return

        grade = frappe.db.get_value("Employee", self.employee, "grade")
        allowed_late_day, deduction_cycle = frappe.db.get_value(
            "Employee Grade",
            grade,
            ["custom_allowed_late_count_days", "custom_late_entry_deduction_cycle"],
        )

        for row in result:
            attendance_date = getdate(row.attendance_date)
            attendance_name = row.name

            # Cancel the existing attendance record
            frappe.db.set_value("Attendance", attendance_name, "docstatus", 2)
            frappe.db.commit()

            # Skip future dates
            if attendance_date > getdate():
                continue

            # Get check-ins for the day
            checkins = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": self.employee,
                    "time": ["between", [attendance_date, add_days(attendance_date, 1)]],
                },
                fields=["*"],
                order_by="time",
            )

            checkins = update_time(checkins)
            shift = checkins[0].shift if checkins else None

            if checkins:
                # Unlink old attendance from check-ins
                update_attendance_in_checkins([c.name for c in checkins], "")

                # Recalculate attendance based on check-ins
                (
                    attendance_status,
                    working_hours,
                    late_entry,
                    early_exit,
                    in_time,
                    out_time,
                ) = get_attendance(checkins, grade, shift)

                attendance = mark_attendance_and_link_log(
                    checkins,
                    attendance_status,
                    attendance_date,
                    working_hours,
                    late_entry,
                    early_exit,
                    in_time,
                    out_time,
                    shift,
                )

                mark_half_day_based_on_deduction_cycle(self.employee, allowed_late_day, deduction_cycle, attendance)

            else:
                # No check-ins → mark as Absent
                frappe.get_doc(
                    {
                        "doctype": "Attendance",
                        "employee": self.employee,
                        "attendance_date": attendance_date,
                        "status": "Absent",
                        "custom_attendance_tag": "A",
                    }
                ).insert(ignore_permissions=True).submit()

    def validate_balance_leaves(self):
        if self.from_date and self.to_date:
            self.total_leave_days = get_number_of_leave_days(
                self.employee, self.leave_type, self.from_date, self.to_date, self.half_day, self.half_day_date
            )

            if self.total_leave_days <= 0:
                frappe.throw(
                    _("The day(s) on which you are applying for leave are holidays. You need not apply for leave.")
                )

            if not is_lwp(self.leave_type):
                leave_balance = get_leave_balance_on(
                    self.employee,
                    self.leave_type,
                    self.from_date,
                    self.to_date,
                    consider_all_leaves_in_the_allocation_period=True,
                    for_consumption=True,
                )
                self.leave_balance = leave_balance.get("leave_balance")
                leave_balance_for_consumption = leave_balance.get("leave_balance_for_consumption")

                if self.status != "Rejected" and (
                    leave_balance_for_consumption < self.total_leave_days or not leave_balance_for_consumption
                ):
                    self.show_insufficient_balance_message(leave_balance_for_consumption)

    def show_insufficient_balance_message(self, leave_balance_for_consumption: float) -> None:
        emp_grade = frappe.get_value("Employee", self.employee, "grade")
        advance_leave = frappe.db.get_value(
            "Employee Grade",
            emp_grade,
            ["custom_allow_advance_leave", "custom_max_no_of_advance_debit", "custom_leave_type"],
        )
        is_advance_allowed = advance_leave[0]
        allowed_advance_debit = -abs(advance_leave[1]) or 0
        leave_type = advance_leave[2]
        if frappe.db.get_value("Leave Type", self.leave_type, "allow_negative"):
            if leave_balance_for_consumption != self.leave_balance:
                msg = _("Warning: Insufficient leave balance for Leave Type {0} in this allocation.").format(
                    frappe.bold(self.leave_type)
                )
                msg += "<br><br>"
                msg += _(
                    "Actual balances aren't available because the leave application spans over different leave allocations. You can still apply for leaves which would be compensated during the next allocation."
                )
            else:
                msg = _("Warning: Insufficient leave balance for Leave Type {0}.").format(frappe.bold(self.leave_type))

            frappe.msgprint(msg, title=_("Warning"), indicator="orange")
        elif is_advance_allowed and allowed_advance_debit and leave_type == self.leave_type:
            actual_balance = get_actual_leave_balance_cf(self.employee, self.leave_type)
            if allowed_advance_debit > (actual_balance - self.total_leave_days):
                frappe.throw(
                    _(
                        "Insufficient leave balance for Leave Type {0}, You have reached maximum allowed advance leave"
                    ).format(frappe.bold(self.leave_type)),
                    exc=InsufficientLeaveBalanceError,
                    title=_("Insufficient Balance"),
                )

        else:
            frappe.throw(
                _("Insufficient leave balance for Leave Type {0}").format(frappe.bold(self.leave_type)),
                exc=InsufficientLeaveBalanceError,
                title=_("Insufficient Balance"),
            )

    def validate_attendance(self):
        # Logic is updated based on the half day checking and attendance status

        attendances = frappe.db.sql(
            """select name,attendance_date,status from `tabAttendance` where employee = %s and (attendance_date between %s and %s) and docstatus = 1""",
            (self.employee, self.from_date, self.to_date),
        )
        for att in attendances:
            if getdate(self.from_date) <= att[1] <= getdate(self.to_date):
                if self.half_day_date and getdate(att[1]) == getdate(self.half_day_date) and att[2] == "Present":
                    frappe.throw(
                        _("Attendance for employee {0} is already marked for day: {1}").format(
                            self.employee, format_date(att[1])
                        ),
                        AttendanceAlreadyMarkedError,
                    )
                elif att[2] == "Present":
                    frappe.throw(
                        _(
                            "Attendance for employee {0} is already marked as Present for day: <br> <ul><li>{1}</li></ul>"
                        ).format(self.employee, format_date(att[1])),
                        AttendanceAlreadyMarkedError,
                    )
                elif att[2] == "Half Day":
                    if not self.half_day_date or getdate(att[1]) != getdate(self.half_day_date):
                        frappe.throw(
                            _(
                                "Attendance for employee {0} is already marked as Half Day for day: <br> <ul><li>{1}</li></ul>"
                            ).format(self.employee, format_date(att[1])),
                            AttendanceAlreadyMarkedError,
                        )
