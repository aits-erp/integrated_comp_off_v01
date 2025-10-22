# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import calendar
from datetime import date

import frappe
from frappe.utils import add_days, format_date, get_time, getdate
from frappe.utils.caching import redis_cache

month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def execute(filters=None):
    month = filters.get("month")
    year = int(filters.get("year"))
    columns, data = get_columns(month, year), []
    company = filters.get("company")
    branch = filters.get("branch")
    division = filters.get("division")
    department = filters.get("department")
    employee = filters.get("employee")
    employees = get_employees(company, branch, division, department, employee)
    dates = get_dates(month, year)
    employee_names = [emp.name for emp in employees]
    attendance_map = get_attendance(employee_names, dates[0], dates[-1], month, year)

    for employee in employees:
        info = {"sr": "PAYCODE, CARD NO. & NAME"}

        emp_data = attendance_map.get(employee.name, {})
        max_checkins = emp_data.get("max_checkins", 0)

        max_pairs = 0
        pairs = ((max_checkins) + 1) // 2
        max_pairs = max(max_pairs, pairs)

        (row_keys, hours_worked, extra_worked, status, shift) = get_rows(max_pairs, dates)
        total_present = 0
        total_absent = 0
        total_hours = 0.0

        for _date in dates:
            date_str = format_date(_date)
            emp_date_data = emp_data.get(date_str, {})
            checkins_on_date = emp_date_data.get("checkins", [])
            emp_checkins = sorted(checkins_on_date, key=lambda x: x.time)
            in_out_logs = get_logs(emp_checkins)
            attendance_on_date = emp_date_data.get("attendance", [])

            for i in range(0, len(row_keys), 2):
                pair_index = i // 2
                in_row = row_keys[i]

                if in_out_logs and pair_index < len(in_out_logs.get("IN", [])):
                    in_row[date_str] = get_time(in_out_logs["IN"][pair_index]["time"])

                if i + 1 < len(row_keys):
                    out_row = row_keys[i + 1]
                    if in_out_logs and pair_index < len(in_out_logs.get("OUT", [])):
                        out_row[date_str] = get_time(in_out_logs["OUT"][pair_index]["time"])
            worked_hours = 0.0
            day_status = "A"
            if attendance_on_date:
                for attendance in attendance_on_date:
                    worked_hours += attendance.get("working_hours", 0.0)
                    day_status = attendance.get("custom_attendance_tag", None) or attendance.get("status")
                    tag = attendance.get("custom_attendance_tag", None)
                    if tag in ["P", "POH", "EW"]:
                        total_present += 1
                    elif tag == "A":
                        total_absent += 1
                    elif tag == "HD":
                        total_absent += 0.5
                        total_present += 0.5
            else:
                total_absent += 1
            total_hours += worked_hours
            hours_worked[date_str] = worked_hours if worked_hours else ""
            status[date_str] = day_status

            shift[date_str] = attendance_on_date[0].get("shift", "") if attendance_on_date else ""

        summary_dates = []
        temp_date = dates[0]
        for _ in range(8):
            summary_dates.append(format_date(temp_date))
            temp_date = add_days(temp_date, days=1)

        if len(summary_dates) >= 8:
            info[summary_dates[0]] = employee["name"]
            info[summary_dates[1]] = employee["employee_name"]
            info[summary_dates[2]] = employee.get("designation", "")
            info[summary_dates[3]] = employee.get("department", "")
            info[summary_dates[4]] = f"Present: {total_present}"
            info[summary_dates[5]] = f"Absent: {total_absent}"
            info[summary_dates[6]] = f"Hours: {round(total_hours / 3600, 2)}"

        data.append(info)
        data.extend(row_keys)
        data.append(hours_worked)
        data.append(extra_worked)
        data.append(status)
        data.append(shift)

    return columns, data


def get_columns(month: str, year: int):
    columns = [{"fieldname": "sr", "fieldtype": "Data", "label": "", "width": "250"}]
    dates = get_dates(month, year)
    for _date in dates:
        columns.append(
            {
                "fieldname": format_date(_date),
                "fieldtype": "Data",
                "label": format_date(_date),
                "width": "70px",
            }
        )
    return columns


@redis_cache
def get_dates(month: str, year: int):
    month_index = month_order.index(month) + 1
    start_date = date(year, month_index, 1)
    last_day = calendar.monthrange(year, month_index)[1]
    end_date = date(year, month_index, last_day)

    dates = []
    while start_date <= end_date:
        dates.append(start_date)
        start_date = add_days(start_date, 1)
    return dates


def get_employees(company, branch, division=None, department=None, employee=None):
    filters = {"company": company, "branch": branch, "status": "Active"}
    if division:
        filters["custom_division"] = division
    if department:
        filters["department"] = department
    if employee:
        filters["name"] = employee

    return frappe.get_all("Employee", filters=filters, fields=["*"])


def get_attendance(employees: list, start_date: date, end_date: date, month: str, year: int):
    dates = get_dates(month, year)
    data = frappe.get_all(
        "Attendance",
        filters={
            "employee": ["in", employees],
            "attendance_date": ["between", (start_date, end_date)],
            "docstatus": ["!=", 2],
        },
        fields=["*"],
    )
    employee_checkins = frappe.get_all(
        "Employee Checkin",
        or_filters={"attendance": ["in", [d.name for d in data]], "shift_start": ["between", (start_date, end_date)]},
        fields=["*"],
    )
    attendance_map = {}
    for employee in employees:
        attendance = [d for d in data if d.employee == employee]
        checkins = [d for d in employee_checkins if d.employee == employee]
        attendance_map[employee] = {"max_checkins": 0}
        for _date in dates:
            attendance_map[employee][format_date(_date)] = {}
            date = getdate(_date)
            attendance_on_date = [d for d in attendance if getdate(d.attendance_date) == date]
            checkins_on_date = [d for d in checkins if getdate(d.shift_start) == date]
            length = len(checkins_on_date)
            if length > attendance_map[employee]["max_checkins"]:
                attendance_map[employee]["max_checkins"] = length
            attendance_map[employee][format_date(date)]["attendance"] = attendance_on_date
            attendance_map[employee][format_date(date)]["checkins"] = checkins_on_date

    return attendance_map


def get_rows(pairs, dates):
    paired_rows = []

    for i in range(pairs):
        in_row = {"sr": f"IN{i + 1}"}
        out_row = {"sr": f"OUT{i + 1}"}

        for _date in dates:
            date_str = format_date(_date)
            in_row[date_str] = ""
            out_row[date_str] = ""
        paired_rows.append(in_row)
        paired_rows.append(out_row)

    hours_worked_row = {"sr": "H Work"}
    extra_hours_worked_row = {"sr": "E Work"}
    status_row = {"sr": "Status"}
    shift_row = {"sr": "Shift"}
    return paired_rows, hours_worked_row, extra_hours_worked_row, status_row, shift_row


def get_logs(employee_checkins):
    data = {"IN": [], "OUT": []}
    for checkin in employee_checkins:
        data[checkin.log_type].append(checkin)
    return data
