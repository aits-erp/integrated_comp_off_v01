import frappe
from erpnext.buying.doctype.supplier_scorecard.supplier_scorecard import daterange
from frappe.utils import getdate
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication

from real_group.utils import get_holiday_dates_for_employee


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
