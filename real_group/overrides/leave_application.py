import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from frappe import _
from frappe.utils import format_date, getdate
from hrms.hr.doctype.leave_application.leave_application import (
    AttendanceAlreadyMarkedError,
    InsufficientLeaveBalanceError,
    LeaveApplication,
    get_leave_balance_on,
    get_number_of_leave_days,
    is_lwp,
)

from real_group.utils import get_actual_leave_balance_cf, get_holiday_dates_for_employee


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
            if attendance_name:
                attendance = frappe.get_doc("Attendance", attendance_name)
                if attendance.docstatus == 1:
                    attendance.cancel()
                    attendance_name = None

            if date in holiday_dates:
                if attendance_name:
                    attendance = frappe.get_doc("Attendance", attendance_name)
                    attendance.flags.ignore_permissions = True
                    if attendance.docstatus == 1:
                        attendance.cancel()
                    frappe.delete_doc("Attendance", attendance_name, force=1)
                continue

            self.create_or_update_attendance(attendance_name, date)

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
        attendance = frappe.db.sql(
            """select name,attendance_date from `tabAttendance` where employee = %s and (attendance_date between %s and %s)
                    and status = 'Present' and docstatus = 1""",
            (self.employee, self.from_date, self.to_date),
        )
        if attendance:
            frappe.throw(
                _("Attendance for employee {0} is already marked for day: <br> <ul>{1}</ul>").format(
                    self.employee, "".join(["<li>{0}</li>".format(format_date(d[1])) for d in attendance])
                ),
                AttendanceAlreadyMarkedError,
            )
