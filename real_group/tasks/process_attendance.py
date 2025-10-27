from datetime import datetime, time, timedelta
from itertools import groupby

import frappe
from frappe.utils import (
    add_days,
    cint,
    format_time,
    get_datetime,
    get_first_day,
    get_last_day,
    get_time,
    get_timedelta,
    getdate,
)
from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours, mark_attendance_and_link_log

from real_group.utils import convert_time_to_hours, convert_time_to_minutes, is_holiday_for_employee


def process(from_date=None):
    # from_date = add_days(getdate(), 1)
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
        group = update_time(group)
        holiday = is_holiday_for_employee(employee, start_date)
        emp_grade = frappe.get_value("Employee", employee, "grade")
        allowed_late_day, deduction_cycle = frappe.db.get_value(
            "Employee Grade",
            emp_grade,
            ["custom_allowed_late_count_days", "custom_late_entry_deduction_cycle"],
        )
        if holiday and not group:
            frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "attendance_date": start_date,
                    "status": "Present",
                    "custom_attendance_tag": "HO" if not holiday.get("is_weekly_holiday") else "WO",
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
            update_status(attendance, attendance_status, holiday)
            mark_half_day_based_on_deduction_cycle(employee, allowed_late_day, deduction_cycle, attendance)
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
        group = update_time(group)
        holiday = is_holiday_for_employee(employee, start_date)
        emp_grade = frappe.get_value("Employee", employee, "grade")
        allowed_late_day, deduction_cycle = frappe.db.get_value(
            "Employee Grade",
            emp_grade,
            ["custom_allowed_late_count_days", "custom_late_entry_deduction_cycle"],
        )
        if holiday and not group:
            frappe.get_doc(
                {
                    "doctype": "Attendance",
                    "attendance_date": start_date_for_night_shift,
                    "status": "Present",
                    "custom_attendance_tag": "HO" if not holiday.get("is_weekly_holiday") else "WO",
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
            update_status(attendance, attendance_status, holiday)
            mark_half_day_based_on_deduction_cycle(employee, allowed_late_day, deduction_cycle, attendance)
        frappe.db.commit()  # nosemgrep


def mark_half_day_based_on_deduction_cycle(employee, allowed_late_day, deduction_cycle, attendance):
    if not allowed_late_day or not deduction_cycle:
        return
    month_start = get_first_day(attendance.attendance_date)
    month_end = get_last_day(attendance.attendance_date)

    monthly_late_count = frappe.db.count(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": ["between", [month_start, month_end]],
            "late_entry": 1,
        },
    )
    if monthly_late_count > allowed_late_day:
        if monthly_late_count % deduction_cycle == 0 and attendance:
            frappe.db.set_value("Attendance", attendance.name, "status", "Half Day")
            frappe.db.set_value("Attendance", attendance.name, "custom_attendance_tag", "HD")


def update_status(attendance, status, holiday):
    if attendance:
        if status == "Present":
            tag = "P"
        elif status == "Half Day":
            tag = "HD"
        else:
            tag = "A"

        if holiday and holiday.get("is_holiday") and status == "Present":
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
            timedelta(minutes=cint(convert_time_to_minutes(shift.custom_late_entry_grace_period)))
            + (timedelta(minutes=cint(convert_time_to_minutes(grade.custom_late_entry_grace_period))))
        )
    ):
        late_entry = True

    if (
        cint(shift.enable_early_exit_marking)
        and out_time
        and out_time
        < logs[0].shift_end - timedelta(minutes=cint(convert_time_to_minutes(shift.custom_early_exit_grace_period)))
    ):
        early_exit = True

    short_leaves = get_short_leaves(logs[0].employee, getdate(logs[0].shift_start))
    if short_leaves:
        for req in short_leaves:
            start = get_timedelta(format_time(get_time(req.shift_start_time)))
            end = get_timedelta(format_time(get_time(req.punch_time)))
            hours = convert_time_to_hours(abs(end - start))
            total_working_hours += hours

    working_threshold = convert_time_to_hours(shift.custom_working_hours_threshold_for_present)
    half_day_threshold = convert_time_to_hours(shift.custom_working_hours_threshold_for_half_day)
    absent_threshold = convert_time_to_hours(shift.custom_working_hours_threshold_for_absent)

    if working_threshold and total_working_hours >= working_threshold:
        return "Present", total_working_hours, late_entry, early_exit, in_time, out_time
    elif half_day_threshold and total_working_hours < half_day_threshold:
        return "Half Day", total_working_hours, late_entry, early_exit, in_time, out_time
    elif absent_threshold and total_working_hours < absent_threshold:
        return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time
    else:
        return "Absent", total_working_hours, late_entry, early_exit, in_time, out_time


def get_short_leaves(employee, date):
    data = frappe.get_all(
        "Short Leave",
        filters={"employee": employee, "for_date": date, "docstatus": 1},
        fields=["shift_start_time", "punch_time"],
    )
    return data


def update_time(checkins: list):
    for checkin in checkins:
        checkin._backup_time = checkin.time
        checkin.time = checkin.custom_processed_time

    return checkins
