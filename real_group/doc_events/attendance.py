from datetime import timedelta

import frappe
from frappe.utils import add_days, get_timedelta, getdate


def validate(doc, method=None):
    doc.custom_working_hours = timedelta(hours=doc.working_hours)


def on_submit(doc, method=None):
    frappe.enqueue(allocate_c_off, doc=doc, queue="long", enqueue_after_commit=True)


def allocate_c_off(doc):
    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    grade = employee.grade
    grade_doc = frappe.get_cached_doc("Employee Grade", grade, for_update=False)

    if grade_doc.custom_present_on_holiday != "Comp Off" and grade_doc.custom_extra_work_hour != "Comp Off":
        return

    hours = doc.working_hours

    if not hours or hours == 0:
        return

    status = ""
    holiday = frappe.db.exists(
        "Holiday",
        {
            "holiday_date": doc.attendance_date,
            "parent": employee.holiday_list,
            "parenttype": "Holiday List",
            "parentfield": "holidays",
        },
        cache=True,
    )
    if holiday:
        holiday = frappe.get_cached_doc("Holiday", holiday, for_update=False)
        if holiday.weekly_off:
            status = "POW"
        else:
            status = "POH"

    shift = doc.shift
    shift = frappe.get_cached_doc("Shift Type", shift) if shift else None
    if not shift:
        return

    start_delta = get_timedelta(shift.start_time)
    end_delta = get_timedelta(shift.end_time)
    if start_delta < end_delta:
        shift_duration = timedelta(seconds=(end_delta - start_delta).total_seconds()).total_seconds() / 3600
    else:
        shift_duration = (
            timedelta(seconds=(end_delta + timedelta(days=1) - start_delta).total_seconds()).total_seconds() / 3600
        )

    c_matrix = frappe.db.exists("Compensation Matrix", {"shift_duration": timedelta(hours=shift_duration)}, cache=True)
    if not c_matrix:
        return
    c_matrix = frappe.get_cached_doc("Compensation Matrix", c_matrix)

    if hours <= shift_duration:
        return

    if holiday and grade_doc.custom_present_on_holiday == "Comp Off":
        diff = hours
    else:
        diff = hours - shift_duration
        status = "EW"
    worked_hrs_in_delta = timedelta(hours=diff)

    matched_c_matrix = next((m for m in c_matrix.items if m.from_hrs < worked_hrs_in_delta <= m.to_hrs), None)
    if not matched_c_matrix:
        return

    credit = matched_c_matrix.c_off_credit
    if not credit:
        return

    comp_off = frappe.get_doc(
        {
            "doctype": "Compensatory Leave Request",
            "employee": employee.name,
            "work_from_date": getdate(doc.attendance_date),
            "work_end_date": getdate(doc.attendance_date),
            "credit": credit,
            "leave_type": "Compensatory Off",
            "status": f"{status}:{diff}",
            "expiry": add_days(getdate(doc.attendance_date), grade_doc.custom_comp_off_validity),
            "reason": status,
        }
    )
    comp_off.insert(ignore_permissions=True, ignore_if_duplicate=True)
    try:
        comp_off.submit()
    except Exception:
        if comp_off.docstatus.is_submitted():
            comp_off.cancel()
        frappe.log_error(
            frappe.get_traceback(), f"Comp-Off Allocation Failed for {doc.employee} on {doc.attendance_date}"
        )
