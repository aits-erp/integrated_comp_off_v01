# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, get_last_day, get_link_to_form, getdate

from real_group.tasks.process_attendance import process as _process_attendance
from real_group.utils import is_holiday_for_employee


class ReprocessAttendance(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        branch: DF.Link | None
        company: DF.Link
        department: DF.Link | None
        division: DF.Link | None
        employee: DF.Link
        month: DF.Literal["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        reprocess_attendance_bulk: DF.Link | None
        status: DF.Literal["Draft", "In Progress", "Completed", "Error"]
        year: DF.Literal["", "2023", "2024"]
    # end: auto-generated types

    def get_dates(self):
        month = datetime.strptime(self.month, "%b").month
        year = int(self.year)
        from_date = datetime(year, month, 1).date()
        to_date = get_last_day(from_date)
        return from_date, to_date

    def validate_salary_slip(self, from_date, to_date):
        Salary_Slip = frappe.qb.DocType("Salary Slip")
        query = (
            frappe.qb.from_(Salary_Slip)
            .select(Salary_Slip.name, Salary_Slip.employee, Salary_Slip.start_date, Salary_Slip.end_date)
            .where((Salary_Slip.start_date <= from_date) & (Salary_Slip.end_date >= to_date))
        )
        result = query.run(as_dict=True)

        if result and len(result) > 0:
            frappe.throw(
                frappe._("Salary Slip(s) exist for the selected period: {0}").format(
                    ", ".join([get_link_to_form("Salary Slip", r.name) for r in result])
                )
            )

    def get_weekly_off(self):
        offs = frappe.get_all(
            "Weekly Holiday Update Request", filters={"employee": self.employee, "docstatus": 1}, fields=["*"]
        )
        return offs

    def get_weekly_off_based_on_date(self, date, weekly_list):
        # Sort by valid_from in descending order to find the most recent applicable one first
        sorted_weekly_list = sorted(weekly_list, key=lambda w: w.valid_from, reverse=True)
        for w in sorted_weekly_list:
            if date >= w.valid_from:
                return w.weekly_off
        return frappe.db.get_value("Employee", self.employee, "custom_weekly_holiday_list", cache=True)

    def get_link_to_self(self):
        return get_link_to_form("Reprocess Attendance", self.name)

    def process_removal(self):
        from_date, to_date = self.get_dates()
        self.delete_attendance(from_date, to_date)
        self.delete_incentive_log(from_date, to_date)
        self.delete_additional_salary(from_date, to_date)
        self.delete_comp_leave_requests(from_date, to_date)
        frappe.db.commit()  # nosemgrep

    def on_submit(self):
        frappe.enqueue_doc(self.doctype, self.name, "reprocess", queue="long", timeout=3600)

    def reprocess(self):
        self.process_removal()
        from_date, to_date = self.get_dates()
        employee_grade = frappe.db.get_value("Employee", self.employee, "grade")
        grade = frappe.get_doc("Employee Grade", employee_grade)
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
        if getdate(to_date) > getdate():
            end_date = getdate()
        else:
            end_date = getdate(to_date)

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
        weekly_offs = self.get_weekly_off()
        start_date = from_date
        if getdate(to_date) > getdate():
            end_date = getdate()
        else:
            end_date = getdate(to_date)

        while start_date <= add_days(end_date, 1):
            weekly_holiday_name = self.get_weekly_off_based_on_date(start_date, weekly_offs)
            _process_attendance(
                from_date=start_date, employee_names=[self.employee], weekly_holiday_name=weekly_holiday_name
            )
            start_date = add_days(start_date, 1)

    def before_submit(self):
        from_date, to_date = self.get_dates()
        self.validate_salary_slip(from_date, to_date)

        # self.delete_comp_leave_applications(fr_date, processed_till)
        # self.delete_attendance_requests(fr_date, processed_till)

    def delete_attendance(self, from_date=None, to_date=None):
        attendances = frappe.get_all(
            "Attendance",
            filters={"employee": self.employee, "attendance_date": ["between", [from_date, to_date]]},
            pluck="name",
        )

        for attendance in attendances:
            doc = frappe.get_doc("Attendance", attendance)
            doc.add_comment(
                comment_type="Comment",
                text=frappe._("Cancelled by Reprocess Attendance {0}".format(self.get_link_to_self())),
            )
            frappe.db.set_value("Attendance", attendance, "docstatus", 2)

    def delete_comp_leave_requests(self, from_date, to_date):
        leave_requests = frappe.get_all(
            "Compensatory Leave Request",
            filters={
                "employee": self.employee,
                "work_from_date": ["between", [from_date, to_date]],
                "docstatus": 1,
                "leave_type": "Compensatory Off",
            },
            pluck="name",
        )

        for leave in leave_requests:
            a_doc = frappe.get_doc("Compensatory Leave Request", leave)
            a_doc.add_comment(
                comment_type="Comment",
                text=frappe._("Cancelled by Reprocess Attendance {0}".format(self.get_link_to_self())),
            )
            if a_doc.docstatus == 1 and a_doc.status != 2:
                a_doc.cancel()
            else:
                frappe.db.set_value("Compensatory Leave Request", leave, "docstatus", 2)
            frappe.db.set_value("Compensatory Leave Request", leave, "status", "Cancelled")

    def delete_comp_leave_applications(self, fr_date=None, t_date=None):
        emp_cond = f" and employee = '{self.employee}'" if self.employee else ""
        conditions = f"{emp_cond}"

        all_comp_leave_applications = frappe.db.sql(
            f"""
            SELECT ar.name
            FROM `tabLeave Application` ar
            WHERE 1=1
            {conditions}
            AND from_date BETWEEN %s AND %s
            AND to_date BETWEEN %s AND %s
            AND ar.docstatus = 1
            AND ar.leave_type = 'Compensatory Off'
        """,
            (fr_date, t_date, fr_date, t_date),
            as_dict=True,
        )

        if all_comp_leave_applications:
            for a in all_comp_leave_applications:
                a_doc = frappe.get_doc("Leave Application", a.get("name"))
                if a_doc.docstatus == 1:
                    a_doc.cancel()
                    frappe.db.set_value("Leave Application", a.get("name"), "status", "Cancelled")
                    frappe.db.set_value("Leave Application", a.get("name"), "workflow_state", "Cancelled")
                    frappe.db.commit()
                    # a_doc.delete()
                # else:
                # 	a_doc.delete()

    def delete_attendance_requests(self, fr_date=None, t_date=None):
        emp_cond = f" and ar.employee = '{self.employee}'" if self.employee else ""
        conditions = f"{emp_cond}"

        all_attendance_requests = frappe.db.sql(
            f"""
            SELECT ar.name
            FROM `tabAttendance Request` ar
            WHERE 1=1
            {conditions}
            AND from_date BETWEEN '{fr_date}' AND '{t_date}'
            AND to_date BETWEEN '{fr_date}' AND '{t_date}'
            AND ar.docstatus = 1
        """,
            (),
            as_dict=True,
        )

        if all_attendance_requests:
            for a in all_attendance_requests:
                a_doc = frappe.get_doc("Attendance Request", a.get("name"))
                if a_doc.docstatus == 1:
                    a_doc.cancel()
                    frappe.db.set_value("Attendance Request", a.get("name"), "status", "Cancelled")
                    frappe.db.set_value("Attendance Request", a.get("name"), "workflow_state", "Cancelled")
                    frappe.db.commit()

    def delete_additional_salary(self, from_date, to_date):
        salaries = frappe.get_all(
            "Additional Salary",
            filters={
                "employee": self.employee,
                "payroll_date": ["between", [from_date, to_date]],
                "salary_component": "Incentives",
                "type": "Earning",
                "docstatus": 1,
            },
            pluck="name",
        )
        for salary in salaries:
            doc = frappe.get_doc("Additional Salary", salary)
            doc.add_comment(
                comment_type="Comment",
                text=frappe._("Cancelled by Reprocess Attendance {0}".format(self.get_link_to_self())),
            )
            doc.cancel()

    def delete_incentive_log(self, from_date, to_date):
        logs = frappe.get_all(
            "Incentive Log",
            filters={
                "employee": self.employee,
                "from_date": ["between", [from_date, to_date]],
                "to_date": ["between", [from_date, to_date]],
            },
            pluck="name",
        )

        for log in logs:
            log = frappe.get_doc("Incentive Log", log)
            log.add_comment(
                comment_type="Comment",
                text=frappe._("Cancelled by Reprocess Attendance {0}".format(self.get_link_to_self())),
            )
            log.cancel()
