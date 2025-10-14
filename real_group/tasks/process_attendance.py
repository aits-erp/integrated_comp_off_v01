from datetime import datetime, time, timedelta
from itertools import groupby

import frappe
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils import add_days, cint, format_time, get_datetime, get_time, get_timedelta, getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours, mark_attendance_and_link_log


def process(from_date=None):
    start_date = add_days(getdate(from_date), -1)
    end_date = getdate(from_date)
    start_date_for_night_shift = add_days(getdate(from_date), -2)
    end_date_for_night_shift = add_days(getdate(from_date), -1)

    grades = frappe.get_all(
        "Employee Grade", filters={"custom_single_punch_applicable": 0, "custom_no_punch_applicable": 0}, pluck="name"
    )
    employees = frappe.get_all("Employee", filters={"grade": ["in", grades], "status": "Active"}, pluck="name")

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
    for employee, group in groupby(logs, key=lambda x: x["employee"]):
        group = list(group)
        group = update_processed_time_in_logs(group)
        holiday_list_name_for_employee = get_holiday_list_for_employee(employee)
        is_holiday = frappe.db.exists(
            "Holiday",
            {
                "holiday_date": start_date,
                "parent": holiday_list_name_for_employee,
            },
        )
        if is_holiday and not group:
            frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "attendance_date": start_date,
                    "status": "Present",
                    "custom_attendance_tag": "HO",
                },
            ).insert(ignore_permissions=True)
        else:
            employee_doc = frappe.get_cached_doc("Employee", employee)
            shift = group[0].shift
            (
                attendance_status,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
            ) = get_attendance(group, employee_doc.grade, shift)
            attendance = mark_attendance_and_link_log(
                group, attendance_status, start_date, working_hours, late_entry, early_exit, in_time, out_time, shift
            )
            update_status(attendance, attendance_status, is_holiday)
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
    for employee, group in groupby(night_logs, key=lambda x: x["employee"]):
        group = list(group)
        group = update_processed_time_in_logs(group)
        holiday_list_name_for_employee = get_holiday_list_for_employee(employee)
        is_holiday = frappe.db.exists(
            "Holiday",
            {
                "holiday_date": start_date_for_night_shift,
                "parent": holiday_list_name_for_employee,
            },
        )
        if is_holiday and not group:
            frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "attendance_date": start_date_for_night_shift,
                    "status": "Present",
                    "custom_attendance_tag": "HO",
                },
            ).insert(ignore_permissions=True)
        else:
            shift = group[0].shift
            employee_doc = frappe.get_cached_doc("Employee", employee)
            (
                attendance_status,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
            ) = get_attendance(group, employee_doc.grade, shift)
            attendance = mark_attendance_and_link_log(
                group,
                attendance_status,
                start_date_for_night_shift,
                working_hours,
                late_entry,
                early_exit,
                in_time,
                out_time,
                shift,
            )
            update_status(attendance, attendance_status, is_holiday)
        frappe.db.commit()  # nosemgrep


def update_status(attendance, status, is_holiday):
    if attendance:
        if status == "Present":
            tag = "P"
        elif status == "Half Day":
            tag = "HD"
        else:
            tag = "A"

        if is_holiday and status == "Present":
            tag = "POH"
        frappe.db.set_value("Attendance", attendance.name, "custom_attendance_tag", tag)


def get_attendance(logs, grade, shift_type):
    if len(logs) < 2:
        return "Absent", 0, False, False, None, None

    late_entry = early_exit = False
    total_working_hours, in_time, out_time = calculate_working_hours(
        logs, "Strictly based on Log Type in Employee Checkin", "Every Valid Check-in and Check-out"
    )
    grade = frappe.get_cached_doc("Employee Grade", grade)
    shift = frappe.get_cached_doc("Shift Type", shift_type)
    if (
        cint(shift.enable_late_entry_marking)
        and in_time
        and in_time
        > logs[0].shift_start
        + (
            timedelta(minutes=cint(shift.late_entry_grace_period))
            + (timedelta(minutes=cint(grade.custom_late_entry_grace_period)))
        )
    ):
        late_entry = True

    if (
        cint(shift.enable_early_exit_marking)
        and out_time
        and out_time < logs[0].shift_end - timedelta(minutes=cint(shift.early_exit_grace_period))
    ):
        early_exit = True

    attendance_request = get_attendance_request(logs[0].employee, getdate(logs[0].shift_start))
    if attendance_request:
        for req in attendance_request:
            start = get_timedelta(format_time(get_time(req.custom_from_time)))
            end = get_timedelta(format_time(get_time(req.custom_to_time)))
            hours = abs(end - start)
            total_working_hours += hours

    if shift.working_hours_threshold_for_absent and total_working_hours < shift.working_hours_threshold_for_absent:
        return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time

    if shift.working_hours_threshold_for_half_day and total_working_hours < shift.working_hours_threshold_for_half_day:
        return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time

    return "Present", total_working_hours, late_entry, early_exit, in_time, out_time


def get_attendance_request(employee, date):
    data = frappe.get_all(
        "Attendance Request",
        filters={"employee": employee, "from_date": ["<=", date], "to_date": [">=", date], "docstatus": 1},
        fields=["custom_from_time", "custom_to_time"],
    )
    return data


def update_processed_time_in_logs(logs):
    for log in logs:
        punch_time = log.time
        processed_time = log.custom_processed_time or punch_time
        log.time = processed_time
        log._time = punch_time

    return logs
