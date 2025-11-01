import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from frappe import _
from frappe.utils import format_date, getdate
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
from real_group.utils import (
    get_actual_leave_balance_cf,
    get_holiday_dates_for_employee,
)


class LeaveApplicationOverride(LeaveApplication):
    def update_attendance(self):
        if self.status != "Approved":
            return

        holiday_dates = []
        grade = frappe.get_value("Employee", self.employee, "grade")
        # Override based on the grade level settings
        if not frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag"):
            holiday_dates = get_holiday_dates_for_employee(self.employee, self.from_date, self.to_date)

        for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
            date = dt.strftime("%Y-%m-%d")
            attendance_name = frappe.db.exists(
                "Attendance", dict(employee=self.employee, attendance_date=date, docstatus=("!=", 2))
            )

            if date in holiday_dates:
                if attendance_name:
                    attendance = frappe.get_doc("Attendance", attendance_name)
                    attendance.flags.ignore_permissions = True
                    if attendance.docstatus == 1:
                        attendance.cancel()
                    # frappe.delete_doc("Attendance", attendance_name, force=1)
                continue

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
        if self.docstatus == 2:
            Attendance = frappe.qb.DocType("Attendance")
            query = (
                frappe.qb.from_(Attendance)
                .select(Attendance.name)
                .where(
                    (Attendance.employee == self.employee)
                    & (Attendance.attendance_date.between(self.from_date, self.to_date))
                    & (Attendance.docstatus < 2)
                    & (Attendance.status.isin(["On Leave", "Half Day"]) | (Attendance.leave_application == self.name))
                )
            )
            grade = frappe.get_value("Employee", self.employee, "grade")
            allowed_late_day, deduction_cycle = frappe.db.get_value(
                "Employee Grade",
                grade,
                ["custom_allowed_late_count_days", "custom_late_entry_deduction_cycle"],
            )
            result = query.run(as_dict=True)
            attendance_names = [row.name for row in result]
            for name in attendance_names:
                attendance_doc = frappe.get_doc("Attendance", name)
                if attendance_doc.attendance_date == self.half_day_date and self.half_day:
                    checkins = frappe.get_all(
                        "Employee Checkin",
                        filters={"employee": self.employee, "attendance": attendance_doc.name},
                        fields=["*"],
                        order_by="time",
                    )
                    checkins = update_time(checkins)
                    shift = checkins[0].shift if checkins else None
                    frappe.db.set_value("Attendance", name, "docstatus", 2)
                    if checkins:
                        update_attendance_in_checkins([checkin.name for checkin in checkins], "")

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
                            attendance_doc.attendance_date,
                            working_hours,
                            late_entry,
                            early_exit,
                            in_time,
                            out_time,
                            shift,
                        )
                        mark_half_day_based_on_deduction_cycle(
                            self.employee, allowed_late_day, deduction_cycle, attendance
                        )
                    else:
                        attendance = (
                            frappe.get_doc(
                                {
                                    "doctype": "Attendance",
                                    "employee": self.employee,
                                    "attendance_date": attendance_doc.attendance_date,
                                    "status": "Absent",
                                    "custom_attendance_tag": "A",
                                }
                            )
                            .insert(ignore_permissions=True)
                            .submit()
                        )

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
            "Employee Grade", emp_grade, ["custom_allow_advance_leave", "custom_max_no_of_advance_debit"]
        )
        is_advance_allowed = advance_leave[0]
        allowed_advance_debit = -abs(advance_leave[1]) or 0
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
        elif is_advance_allowed:
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
