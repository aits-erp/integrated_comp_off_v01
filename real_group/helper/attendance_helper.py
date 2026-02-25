from datetime import date, timedelta

import frappe
from frappe.utils import (
    add_days,
    cint,
    format_time,
    get_first_day,
    get_last_day,
    get_time,
    get_timedelta,
    getdate,
)

from hrms.hr.doctype.employee_checkin.employee_checkin import (
    calculate_working_hours,
    mark_attendance_and_link_log,
    update_attendance_in_checkins,
)

from real_group.utils import (
    convert_time_to_hours,
    convert_time_to_minutes,
    get_holiday_dates_for_employee,
    is_holiday_for_employee,
)


# --------------------------------------------------------
# Helpers
# --------------------------------------------------------


def has_valid_in_out_pair(logs) -> bool:
    has_in = False
    has_out = False

    for log in logs or []:
        log_type = (
            log.get("log_type")
            if hasattr(log, "get")
            else getattr(log, "log_type", None)
        )
        if log_type == "IN":
            has_in = True
        elif log_type == "OUT":
            has_out = True
        if has_in and has_out:
            return True

    return False


def update_time(checkins: list):
    checkins = sorted(checkins, key=lambda x: x["time"])
    for checkin in checkins:
        checkin._backup_time = checkin.time
        checkin.time = checkin.custom_processed_time
    return checkins


def has_attendance(employee, attendance_date):
    return frappe.db.exists(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date,
            "docstatus": ["<", 2],
        },
    )


# --------------------------------------------------------
# Main Attendance Engine
# --------------------------------------------------------


def create_attendance(
    employee: str, date: str | date, logs: list | None, reprocess_ref=None
):

    employee_doc = frappe.get_cached_doc("Employee", employee)

    if logs:
        logs = update_time(logs)

    if isinstance(date, str):
        date = getdate(date)

    existing_attendance = has_attendance(employee, date)
    holiday = is_holiday_for_employee(employee, date)

    emp_grade = frappe.get_value("Employee", employee, "grade")
    allowed_late_day, deduction_cycle = frappe.db.get_value(
        "Employee Grade",
        emp_grade,
        ["custom_allowed_late_count_days", "custom_late_entry_deduction_cycle"],
    )

    # --------------------------------------------------------
    # CASE 1 — Attendance already exists (reprocess / night shift safe)
    # --------------------------------------------------------

    if existing_attendance:
        existing_attendance = frappe.get_doc("Attendance", existing_attendance)

        if logs:
            shift = logs[0].shift

            status, hours, late, early, in_time, out_time = get_attendance(
                logs, employee_doc.grade, shift
            )

            final_status = status

            if holiday and not holiday.get("is_half_day"):
                final_status = "Present"

            if existing_attendance.status == "Absent":
                existing_attendance.db_set(
                    {
                        "status": final_status,
                        "working_hours": hours,
                        "shift": shift,
                        "late_entry": late,
                        "early_exit": early,
                        "in_time": in_time,
                        "out_time": out_time,
                        "custom_reprocess_reference": reprocess_ref,
                    }
                )

            elif (
                existing_attendance.status == "Half Day"
                and existing_attendance.leave_application
            ):
                if status == "Half Day":
                    status = "Present"
                if status == "Absent":
                    status = "Half Day"

                existing_attendance.db_set(
                    {
                        "status": status,
                        "working_hours": hours
                        + (existing_attendance.working_hours or 0),
                        "shift": shift,
                        "late_entry": late,
                        "early_exit": early,
                        "in_time": in_time,
                        "out_time": out_time,
                        "custom_reprocess_reference": reprocess_ref,
                    }
                )
            else:
                existing_attendance.db_set(
                    {
                        "working_hours": hours
                        + (existing_attendance.working_hours or 0),
                        "shift": existing_attendance.shift or shift,
                        "custom_reprocess_reference": reprocess_ref,
                    }
                )

            update_attendance_in_checkins(
                [c.name for c in logs], existing_attendance.name
            )

            try:
                from real_group.doc_events.attendance import (
                    allocate_c_off,
                    allocate_incentive,
                    update_attendance_tag,
                )

                update_attendance_tag(existing_attendance)
                if not reprocess_ref:
                    allocate_incentive(existing_attendance)
                    allocate_c_off(existing_attendance)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Attendance tag update failed")

        return

    # --------------------------------------------------------
    # CASE 2 — Holiday without logs
    # --------------------------------------------------------

    if holiday and not logs:
        tag = "WO" if holiday.get("is_weekly_off") else "HO"
        status = "Half Day" if holiday.get("is_half_day") else "Present"

        frappe.get_doc(
            {
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": date,
                "status": status,
                "custom_attendance_tag": tag,
                "custom_reprocess_reference": reprocess_ref,
            }
        ).insert(ignore_permissions=True).submit()
        return

    # --------------------------------------------------------
    # CASE 3 — Normal working day
    # --------------------------------------------------------

    if logs and not holiday:
        shift = logs[0].shift

        status, hours, late, early, in_time, out_time = get_attendance(
            logs, employee_doc.grade, shift
        )

        attendance = mark_attendance_and_link_log(
            logs,
            status,
            date,
            hours,
            late,
            early,
            in_time,
            out_time,
            shift,
        )

        attendance.db_set("custom_reprocess_reference", reprocess_ref)

        mark_half_day_based_on_deduction_cycle(
            employee, allowed_late_day, deduction_cycle, attendance
        )
        return

    # --------------------------------------------------------
    # CASE 4 — Holiday with logs (POW / POH logic)
    # --------------------------------------------------------

    if logs and holiday:
        is_half = holiday.get("is_half_day")
        is_weekly_off = holiday.get("is_weekly_off")

        base_tag = "WO" if is_weekly_off else "HO"

        shift = logs[0].shift

        status, hours, late, early, in_time, out_time = get_attendance(
            logs, employee_doc.grade, shift
        )

        final_status = status
        final_tag = base_tag

        if is_half and status == "Half Day":
            final_status = "Present"

        if not is_half:
            final_status = "Present"

            if has_valid_in_out_pair(logs):
                final_tag = "POW" if is_weekly_off else "POH"

        doc = frappe.get_doc(
            {
                "doctype": "Attendance",
                "employee": employee,
                "attendance_date": date,
                "status": final_status,
                "working_hours": hours,
                "shift": shift,
                "late_entry": late,
                "early_exit": early,
                "in_time": in_time,
                "out_time": out_time,
                "custom_attendance_tag": final_tag,
                "custom_reprocess_reference": reprocess_ref,
            }
        ).insert(ignore_permissions=True)

        doc.submit()
        update_attendance_in_checkins([c.name for c in logs], doc.name)
        return

    # --------------------------------------------------------
    # CASE 5 — Absent
    # --------------------------------------------------------

    frappe.get_doc(
        {
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": date,
            "status": "Absent",
            "custom_attendance_tag": "A",
            "custom_reprocess_reference": reprocess_ref,
        }
    ).insert(ignore_permissions=True).submit()


# --------------------------------------------------------
# Core Attendance Computation (unchanged — was correct)
# --------------------------------------------------------


def get_attendance(logs, grade, shift_type):

    if len(logs) < 2:
        return "Absent", 0, False, False, None, None

    late_entry = early_exit = False

    total_working_hours, in_time, out_time = calculate_working_hours(
        logs,
        "Strictly based on Log Type in Employee Checkin",
        "Every Valid Check-in and Check-out",
    )

    grade = frappe.get_cached_doc("Employee Grade", grade)
    shift = frappe.get_cached_doc("Shift Type", shift_type)

    force_half_day_due_to_late = False

    if cint(shift.enable_late_entry_marking) and in_time:
        shift_grace = convert_time_to_minutes(shift.custom_late_entry_grace_period)
        grade_grace = convert_time_to_minutes(grade.custom_late_entry_grace_period)
        grace = max(shift_grace, grade_grace)

        shift_grace_time = logs[0].shift_start + timedelta(minutes=shift_grace)
        grade_grace_time = logs[0].shift_start + timedelta(minutes=grade_grace)

        if in_time <= shift_grace_time:
            late_entry = False
        elif in_time <= grade_grace_time:
            late_entry = True
        else:
            force_half_day_due_to_late = True

    if (
        cint(shift.enable_early_exit_marking)
        and out_time
        and out_time
        < logs[0].shift_end
        - timedelta(
            minutes=convert_time_to_minutes(shift.custom_early_exit_grace_period)
        )
    ):
        early_exit = True

    short_leaves = get_short_leaves(logs[0].employee, getdate(logs[0].shift_start))
    for req in short_leaves:
        start = get_timedelta(format_time(get_time(req.shift_start_time)))
        end = get_timedelta(format_time(get_time(req.punch_time)))
        total_working_hours += convert_time_to_hours(abs(end - start))

    working_threshold = convert_time_to_hours(
        shift.custom_working_hours_threshold_for_present
    )
    half_day_threshold = convert_time_to_hours(
        shift.custom_working_hours_threshold_for_half_day
    )
    absent_threshold = convert_time_to_hours(
        shift.custom_working_hours_threshold_for_absent
    )

    if working_threshold and total_working_hours >= working_threshold:
        status = "Present"
    elif half_day_threshold and total_working_hours >= half_day_threshold:
        status = "Half Day"
    elif absent_threshold and total_working_hours < absent_threshold:
        status = "Absent"
    else:
        status = "Absent"

    if force_half_day_due_to_late and status == "Present":
        status = "Half Day"

    if late_entry and status == "Half Day":
        late_entry = False

    return status, total_working_hours, late_entry, early_exit, in_time, out_time


def get_short_leaves(employee, date):
    return frappe.get_all(
        "Short Leave",
        filters={"employee": employee, "for_date": date, "docstatus": 1},
        fields=["shift_start_time", "punch_time"],
    )


def mark_half_day_based_on_deduction_cycle(
    employee, allowed_late_day, deduction_cycle, attendance
):

    if not allowed_late_day or not deduction_cycle:
        return

    if not attendance or not attendance.late_entry or attendance.status != "Present":
        return

    month_start = get_first_day(attendance.attendance_date)
    month_end = get_last_day(attendance.attendance_date)

    holiday_dates = get_holiday_dates_for_employee(employee, month_start, month_end)

    working_days = []
    while month_start <= month_end:
        if month_start not in holiday_dates:
            working_days.append(month_start)
        month_start = add_days(month_start, 1)

    late_count = frappe.db.count(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": ["in", working_days],
            "docstatus": 1,
            "status": ["in", ["Present", "Half Day"]],
            "late_entry": 1,
        },
    )

    if late_count > allowed_late_day and late_count % deduction_cycle == 0:
        frappe.db.set_value("Attendance", attendance.name, "status", "Half Day")
        frappe.db.set_value(
            "Attendance", attendance.name, "custom_attendance_tag", "HD"
        )
