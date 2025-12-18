# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import calendar
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import add_days, format_date, get_time, getdate
from frappe.utils.caching import redis_cache

from real_group.utils import is_holiday_for_employee

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
    shifts = get_shifts()
    for employee in employees:
        info = {"sr": "PAYCODE, CARD NO. & NAME"}

        emp_data = attendance_map.get(employee.name, {})
        max_checkins = emp_data.get("max_checkins", 0)

        max_pairs = 0
        pairs = ((max_checkins) + 1) // 2
        max_pairs = max(max_pairs, pairs)

        (row_keys, hours_worked, extra_worked, processed_status, status, shift) = get_rows(max_pairs, dates)
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
            hours_worked[date_str] = timedelta(seconds=round(worked_hours * 3600 / 60) * 60) if worked_hours else ""
            status[date_str] = day_status

            shift[date_str] = attendance_on_date[0].get("shift", "") if attendance_on_date else ""
            if attendance_on_date and attendance_on_date[0].get("shift", None):
                shift_type = next((s for s in shifts if s.name == attendance_on_date[0].get("shift")), None)
                if shift_type and shift_type.custom_shift_time and worked_hours:
                    shift_time = get_time(shift_type.custom_shift_time)
                    worked_time = get_time(timedelta(hours=worked_hours))
                    if is_holiday_for_employee(employee.name, _date):
                        extra_worked[date_str] = get_time(worked_time)
                    else:
                        dt1 = datetime.combine(date.today(), shift_time)
                        dt2 = datetime.combine(date.today(), worked_time)
                        delta = dt2 - dt1
                        if delta.total_seconds() > 0:
                            extra_worked[date_str] = get_time(delta)

            processed_status[date_str] = get_processed_status(employee.name, _date, emp_date_data, day_status)
        summary_dates = []
        temp_date = dates[0]
        for _ in range(8):
            summary_dates.append(format_date(temp_date))
            temp_date = add_days(temp_date, days=1)

        if len(summary_dates) >= 8:
            total_time = timedelta(seconds=round(total_hours * 3600 / 60) * 60)
            info[summary_dates[0]] = employee["name"]
            info[summary_dates[1]] = employee["employee_name"]
            info[summary_dates[2]] = employee.get("designation", "")
            info[summary_dates[3]] = employee.get("department", "")
            info[summary_dates[4]] = f"Present: {total_present}"
            info[summary_dates[5]] = f"Absent: {total_absent}"
            info[summary_dates[6]] = f"Hours: {total_time}"

        data.append(info)
        data.extend(row_keys)
        data.append(hours_worked)
        data.append(extra_worked)
        data.append(processed_status)
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
    processed_status_row = {"sr": "P Status"}
    status_row = {"sr": "Status"}
    shift_row = {"sr": "Shift"}
    return paired_rows, hours_worked_row, extra_hours_worked_row, processed_status_row, status_row, shift_row


def get_logs(employee_checkins):
    data = {"IN": [], "OUT": []}
    for checkin in employee_checkins:
        data[checkin.log_type].append(checkin)
    return data


@redis_cache
def get_shifts():
    return frappe.get_all("Shift Type", fields=["*"])


def get_processed_status(employee, date, data_on_date, day_status):
    status = day_status
    date = getdate(date)
    attendance = data_on_date.get("attendance", [])
    if attendance:
        attendance = attendance[0]
    checkins = data_on_date.get("checkins", [])
    leave_application_doc = None
    leave_type_doc = None

    if attendance:
        if attendance.leave_application and attendance.leave_type:
            leave_type_doc = frappe.get_cached_doc("Leave Type", attendance.leave_type)
            leave_application_doc = frappe.get_cached_doc("Leave Application", attendance.leave_application)

            leave_from_date = getdate(leave_application_doc.from_date)
            leave_to_date = getdate(leave_application_doc.to_date)

            is_lwp = leave_type_doc.is_lwp
            is_earned = leave_type_doc.is_earned_leave
            is_compensatory = leave_type_doc.is_compensatory

            if leave_from_date <= date <= leave_to_date:
                if is_lwp:
                    status = "LW"
                    if leave_application_doc.half_day_date == date and len(checkins) > 0:
                        status = "HLW"

                if is_compensatory:
                    status = "CO"
                    if leave_application_doc.half_day_date == date:
                        status = "HCO"

                if is_earned:
                    status = "EL"
                    if leave_application_doc.half_day_date == date:
                        status = "HEL"

                if "casual leave" in leave_type_doc.name.lower():
                    status = "CL"
                    if leave_application_doc.half_day_date == date:
                        status = "HCL"

                combo_status = get_half_day_combo_status(employee, date, leave_application_doc, leave_type_doc)
                if combo_status:
                    status = combo_status

        if attendance.attendance_request:
            status = "OD"
            attendance_request = frappe.get_cached_doc("Attendance Request", attendance.attendance_request)
            if attendance_request.half_day_date == date:
                status = "HOD"
                if attendance.leave_application:
                    if attendance.custom_attendance_tag == "EL":
                        status = "ODEL"
                    elif attendance.custom_attendance_tag == "CL":
                        status = "ODCL"
                    elif attendance.custom_attendance_tag == "CO":
                        status = "ODCO"

            if attendance_request.reason == "Mis Punch":
                status = "MIS"

        optional_status = get_optional_half_day_status(
            employee,
            date,
            attendance,
            leave_application_doc,
            leave_type_doc,
            checkins,
            status,
        )
        if optional_status:
            status = optional_status

    day_off_status = get_employee_day_off_status(employee, date, checkins)
    if day_off_status:
        return day_off_status

    return status


def get_employee_day_off_status(employee: str, target_date, checkins=None):
    day_off_data = is_holiday_for_employee(employee, target_date)
    if not day_off_data or not day_off_data.get("is_holiday"):
        return None

    sandwich_status = get_sandwich_absent_status(employee, target_date)
    if sandwich_status:
        return sandwich_status

    od_status = get_day_off_attendance_request_status(employee, target_date)
    if od_status:
        return od_status

    has_checkins = bool(checkins)
    if day_off_data.get("is_weekly_off"):
        return "POW" if has_checkins else "WO"

    return "POH" if has_checkins else "HO"


def get_day_off_attendance_request_status(employee: str, target_date):
    requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
        },
        fields=["half_day", "half_day_date", "reason"],
    )

    for request in requests:
        reason = (request.get("reason") or "").strip().lower()
        if reason not in {"official", "tour"}:
            continue

        if request.get("half_day"):
            half_day_date = request.get("half_day_date")
            if half_day_date and getdate(half_day_date) == target_date:
                return "OD"
            continue

        return "OD"

    return None


def get_sandwich_absent_status(employee: str, target_date):
    attendance = get_attendance_record(employee, target_date)
    if not attendance or not is_absent_attendance(attendance):
        return None

    previous_attendance = get_attendance_record(employee, add_days(target_date, -1))
    next_attendance = get_attendance_record(employee, add_days(target_date, 1))

    if is_leave_attendance(previous_attendance) and is_leave_attendance(next_attendance):
        return "A1"

    return None


def get_attendance_record(employee: str, target_date):
    records = frappe.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": target_date,
            "docstatus": ["!=", 2],
        },
        fields=["name", "status", "leave_type", "leave_application"],
        limit=1,
    )
    return records[0] if records else None


def is_absent_attendance(attendance_doc):
    if not attendance_doc:
        return False
    status = (attendance_doc.get("status") or "").strip().upper()
    return status in {"A", "ABSENT"}


def is_leave_attendance(attendance_doc):
    if not attendance_doc:
        return False
    if attendance_doc.get("leave_type") or attendance_doc.get("leave_application"):
        return True

    status = (attendance_doc.get("status") or "").strip().upper()
    return "leave" in status.lower()


def get_leave_code(leave_type_doc):
    if not leave_type_doc:
        return None
    if leave_type_doc.is_earned_leave:
        return "EL"
    if leave_type_doc.is_compensatory:
        return "CO"
    if leave_type_doc.is_lwp:
        return "LW"
    if "casual leave" in leave_type_doc.name.lower():
        return "CL"
    return None


def get_half_day_combo_status(employee, target_date, primary_application, primary_leave_type):
    if not primary_application or not primary_leave_type:
        return None
    if not primary_application.half_day_date:
        return None
    if getdate(primary_application.half_day_date) != target_date:
        return None

    primary_code = get_leave_code(primary_leave_type)
    if primary_code not in {"EL", "CO", "CL"}:
        return None

    other_half_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
            "half_day_date": target_date,
            "name": ["!=", primary_application.name],
        },
        fields=["name", "leave_type"],
    )

    for other in other_half_leaves:
        other_leave_type = frappe.get_cached_doc("Leave Type", other.leave_type)
        other_code = get_leave_code(other_leave_type)
        if not other_code:
            continue
        codes = {primary_code, other_code}
        if codes == {"EL", "CO"}:
            return "ELCO"
        if codes == {"CL", "CO"}:
            return "CLCO"

    return None


def is_optional_leave_type(leave_type_doc_or_name):
    if not leave_type_doc_or_name:
        return False
    if isinstance(leave_type_doc_or_name, str):
        return bool(frappe.get_cached_value("Leave Type", leave_type_doc_or_name, "is_optional_leave"))
    return bool(getattr(leave_type_doc_or_name, "is_optional_leave", False))


def get_optional_half_day_status(
    employee,
    target_date,
    attendance_doc,
    leave_application_doc,
    leave_type_doc,
    checkins,
    current_status,
):
    if not attendance_doc or not leave_application_doc or not leave_type_doc:
        return None
    if not is_optional_leave_type(leave_type_doc):
        return None
    if not getattr(leave_application_doc, "half_day", False):
        return None
    half_day_date = getattr(leave_application_doc, "half_day_date", None)
    if not half_day_date or getdate(half_day_date) != target_date:
        return None
    attendance_status = (getattr(attendance_doc, "status", "") or "").lower()
    if attendance_status != "half day":
        return None

    other_combo = get_optional_combo_from_other_leave(employee, target_date, leave_application_doc.name)
    if other_combo:
        return other_combo

    request_combo = get_optional_combo_from_attendance_request(attendance_doc, target_date)
    if request_combo:
        return request_combo

    status_combo = get_optional_combo_from_status(current_status)
    if status_combo:
        return status_combo

    if checkins:
        return "PHO"

    return "HHO"


def get_optional_combo_from_other_leave(employee, target_date, primary_application_name):
    if not primary_application_name:
        return None

    other_half_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", target_date],
            "to_date": [">=", target_date],
            "half_day": 1,
            "half_day_date": target_date,
            "name": ["!=", primary_application_name],
        },
        fields=["name", "leave_type"],
    )

    mapping = {"EL": "ELHO", "CL": "CLHO", "CO": "COHO", "LW": "LWHO"}
    for other in other_half_leaves:
        other_leave_type = frappe.get_cached_doc("Leave Type", other.leave_type)
        if is_optional_leave_type(other_leave_type):
            continue
        other_code = get_leave_code(other_leave_type)
        if other_code in mapping:
            return mapping[other_code]

    return None


def get_optional_combo_from_attendance_request(attendance_doc, target_date):
    if not attendance_doc or not attendance_doc.attendance_request:
        return None

    attendance_request = frappe.get_cached_doc("Attendance Request", attendance_doc.attendance_request)
    if not getattr(attendance_request, "half_day", False):
        return None
    half_day_date = getattr(attendance_request, "half_day_date", None)
    if not half_day_date or getdate(half_day_date) != target_date:
        return None

    if attendance_request.reason == "Mis Punch":
        return "PHO"

    return "ODHO"


def get_optional_combo_from_status(current_status):
    if not current_status:
        return None

    status_map = {
        "HEL": "ELHO",
        "HCL": "CLHO",
        "HCO": "COHO",
        "HLW": "LWHO",
        "HOD": "ODHO",
        "MIS": "MHO",
    }
    return status_map.get(current_status)
