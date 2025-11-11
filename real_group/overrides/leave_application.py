import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from frappe import _
from frappe.utils import add_days, format_date, getdate
from hrms.hr.doctype.leave_application.leave_application import (
    AttendanceAlreadyMarkedError,
    InsufficientLeaveBalanceError,
    LeaveApplication,
    get_leave_balance_on,
    get_number_of_leave_days,
    is_lwp,
)

from real_group.doc_events.attendance import allocate_c_off, allocate_incentive, update_attendance_tag
from real_group.helper.attendance_helper import create_attendance
from real_group.utils import get_actual_leave_balance_cf, get_holiday_dates_for_employee, is_holiday_for_employee


class LeaveApplicationOverride(LeaveApplication):
    def validate(self):
        super().validate()
        self.validate_joining_date()

    def validate_joining_date(self):
        joining_date = frappe.db.get_value("Employee", self.employee, "date_of_joining")
        if joining_date and getdate(self.from_date) < joining_date:
            frappe.throw(
                _("Leave cannot be applied before employee's joining date: {0}").format(format_date(joining_date))
            )

    def process_jobs_after_update(self, doc):
        frappe.enqueue(update_attendance_tag, doc=doc, queue="long", enqueue_after_commit=True)
        frappe.enqueue(allocate_c_off, doc=doc, queue="long", enqueue_after_commit=True)
        frappe.enqueue(allocate_incentive, doc=doc, queue="long", enqueue_after_commit=True)

    def update_attendance(self):
        if self.status != "Approved":
            return

        grade = frappe.get_value("Employee", self.employee, "grade")
        apply_sandwich = frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag")

        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)

        # Fetch all dates in range
        all_dates = [d for d in daterange(from_date, to_date)]

        holiday_map = {}
        for d in all_dates:
            info = is_holiday_for_employee(self.employee, d) or {}
            holiday_map[d] = {
                "is_holiday": bool(info.get("is_holiday")),
                "is_half_day": bool(info.get("is_half_day")),  # ← needs to be returned by is_holiday_for_employee()
            }

        status = {}
        for d in all_dates:
            if self.half_day and getdate(self.half_day_date) == d:
                status[d] = "half_leave"
            elif holiday_map[d]["is_holiday"]:
                status[d] = "half_holiday" if holiday_map[d]["is_half_day"] else "full_holiday"
            else:
                status[d] = "full_leave"

        if apply_sandwich:
            i = 0
            n = len(all_dates)
            while i < n:
                d = all_dates[i]
                if status[d] == "full_holiday":  # ← only consider full holidays
                    block_start = i
                    while i < n and status[all_dates[i]] == "full_holiday":
                        i += 1
                    block_end = i - 1

                    prev_d = add_days(all_dates[block_start], -1)
                    next_d = add_days(all_dates[block_end], 1)

                    prev_is_full = prev_d in status and status[prev_d] == "full_leave"
                    next_is_full = next_d in status and status[next_d] == "full_leave"

                    # Only count if both adjacent are full leave days
                    if prev_is_full and next_is_full:
                        for j in range(block_start, block_end + 1):
                            status[all_dates[j]] = "full_leave"
                else:
                    i += 1
        else:
            # Exclude full holidays from attendance update if sandwich not applied
            holiday_dates = get_holiday_dates_for_employee(self.employee, self.from_date, self.to_date)
            all_dates = [d for d in all_dates if d.strftime("%Y-%m-%d") not in holiday_dates]

        for d in all_dates:
            date_str = d.strftime("%Y-%m-%d")
            attendance_name = frappe.db.exists(
                "Attendance", dict(employee=self.employee, attendance_date=date_str, docstatus=("!=", 2))
            )

            day_status = status[d]
            if day_status == "full_holiday":
                continue
            elif apply_sandwich and day_status == "full_leave":
                # If sandwich is applied and this date falls in sandwich block, mark as Absent
                self.create_or_update_attendance(attendance_name, date_str, status="Absent")
            else:
                is_lwp = frappe.db.get_value("Leave Type", self.leave_type, "is_lwp")
                status = (
                    "Half Day"
                    if self.half_day_date and getdate(date_str) == getdate(self.half_day_date)
                    else "On Leave"
                    if not is_lwp
                    else "Absent"
                )
                self.create_or_update_attendance(attendance_name, date_str, status=status)

    def create_or_update_attendance(self, attendance_name, date, status="On Leave"):
        if attendance_name:
            # update existing attendance, change absent to on leave
            doc = frappe.get_doc("Attendance", attendance_name)
            doc.db_set(
                {
                    "status": status,
                    "leave_type": self.leave_type,
                    "leave_application": self.name,
                    "custom_half_type": self.custom_half_type
                    if self.half_day_date and getdate(date) == getdate(self.half_day_date)
                    else None,
                }
            )
            self.process_jobs_after_update(doc)
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
            doc.custom_half_type = (
                self.custom_half_type if self.half_day_date and getdate(date) == getdate(self.half_day_date) else None
            )
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

        for row in result:
            attendance_date = getdate(row.attendance_date)
            attendance_name = row.name

            # Cancel the existing attendance record
            frappe.db.set_value("Attendance", attendance_name, "docstatus", 2)
            frappe.db.commit()

            # Skip future dates
            if attendance_date > getdate():
                continue

            checkins = frappe.get_all(
                "Employee Checkin",
                filters={
                    "employee": self.employee,
                    "time": ["between", [attendance_date, add_days(attendance_date, 1)]],
                },
                fields=["*"],
                order_by="time",
            )
            create_attendance(self.employee, attendance_date, checkins)

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
        # TODO: NEED TO CHECK IF VALIDATION IS REQUIRED OR NOT
        return
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
