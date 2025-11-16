from datetime import datetime, time
from itertools import groupby

import frappe
from frappe.utils import (
    add_days,
    get_datetime,
    getdate,
)

from real_group.helper.attendance_helper import create_attendance


def process(from_date=None, employee_names: list | None = None, reprocess_ref=None):
    start_date = add_days(getdate(from_date), -1)
    end_date = getdate(from_date)
    start_date_for_night_shift = add_days(getdate(from_date), -2)
    end_date_for_night_shift = add_days(getdate(from_date), -1)

    if not employee_names:
        grades = frappe.get_all(
            "Employee Grade",
            filters={"custom_single_punch_applicable": 0, "custom_no_punch_applicable": 0},
            pluck="name",
        )
        employees = frappe.get_all("Employee", filters={"grade": ["in", grades], "status": "Active"}, pluck="name")
    else:
        employees = employee_names

    day_shift_checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employees],
            "shift_start": [">=", get_datetime(start_date)],
            "shift_end": ["<=", get_datetime(end_date)],
            "attendance": ["is", "not set"],
        },
        order_by="time",
        fields=["*"],
    )

    logs = sorted(day_shift_checkins, key=lambda x: (x["employee"], x["time"]))

    # Group logs by employee
    logs_by_employee = {}
    for employee, group in groupby(logs, key=lambda x: x["employee"]):
        logs_by_employee[employee] = list(group)

    # Process all employees, including those without logs
    for employee in employees:
        group = logs_by_employee.get(employee, [])
        create_attendance(employee, start_date, group, reprocess_ref)

        frappe.db.commit()  # nosemgrep

    # Processing Night Shift Employees
    night_shift_checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": ["in", employees],
            "shift_start": [">=", get_datetime(start_date_for_night_shift)],
            "shift_end": ["<=", datetime.combine(end_date_for_night_shift, time(23, 59, 59))],
            "attendance": ["is", "not set"],
        },
        order_by="time",
        fields=["*"],
    )
    night_logs = sorted(night_shift_checkins, key=lambda x: (x["employee"], x["time"]))

    # Group night logs by employee
    night_logs_by_employee = {}
    for employee, group in groupby(night_logs, key=lambda x: x["employee"]):
        night_logs_by_employee[employee] = list(group)

    # Process all employees for night shift, including those without logs
    for employee in employees:
        group = night_logs_by_employee.get(employee, [])
        create_attendance(employee, start_date_for_night_shift, group, reprocess_ref)
        frappe.db.commit()  # nosemgrep
