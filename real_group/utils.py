from datetime import time, timedelta

import frappe
from frappe.utils import get_time, getdate
from hrms.hr.utils import get_leave_allocations
from pypika.functions import Count


def convert_time_to_seconds(time_str: str | time | timedelta) -> float:
    if not time_str:
        return 0.0
    if isinstance(time_str, str):
        time_str = get_time(time_str)
    if isinstance(time_str, timedelta):
        return time_str.total_seconds()
    return timedelta(hours=time_str.hour, minutes=time_str.minute, seconds=time_str.second).total_seconds()


def convert_time_to_minutes(time_str: str | time) -> float:
    if not time_str:
        return 0.0
    seconds = convert_time_to_seconds(time_str)
    return seconds / 60


def convert_time_to_hours(time_str: str | time) -> float:
    if not time_str:
        return 0.0
    seconds = convert_time_to_seconds(time_str)
    return seconds / 3600


def is_holiday_for_employee(employee: str, date):
    from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

    data = {}
    holiday_list = get_holiday_list_for_employee(employee)
    weekly_holiday_list = frappe.get_value("Employee", employee, "custom_weekly_holiday_list")

    is_holiday = frappe.db.get_value(
        "Holiday",
        {
            "parent": holiday_list,
            "holiday_date": getdate(date),
            "parenttype": "Holiday List",
            "parentfield": "holidays",
        },
        ["name", "weekly_off", "custom_unplanned", "custom_half_day"],
    )
    if is_holiday:
        data = {
            "is_holiday": True,
            "holiday_name": is_holiday[0],
            "is_weekly_off": is_holiday[1],
            "is_unplanned_holiday": is_holiday[2],
            "is_half_day": is_holiday[3],
        }
        return data
    else:
        is_holiday = frappe.db.get_value(
            "Weekly Off Holiday",
            {
                "parent": weekly_holiday_list,
                "holiday_date": getdate(date),
                "parenttype": "Weekly Off List",
                "parentfield": "holidays",
            },
            "name",
        )
        if is_holiday:
            data = {
                "is_holiday": True,
                "holiday_name": is_holiday,
                "is_weekly_off": True,
                "is_unplanned_holiday": False,
                "is_half_day": False,
            }
            return data

    return False


def fetch_leaves_for_working_days(employee: str, from_date, to_date, on_working_days: int):
    Leave_Type = frappe.qb.DocType("Leave Type")
    Attendance = frappe.qb.DocType("Attendance")
    query = (
        frappe.qb.from_(Attendance)
        .left_join(Leave_Type)
        .on(Attendance.leave_type == Leave_Type.name)
        .select(Count(Attendance.name))
        .where(
            (Attendance.employee == employee)
            & (Attendance.attendance_date.between(from_date, to_date))
            & (Attendance.status.notin(["Absent"]))
            & (Leave_Type.is_lwp == 0)
        )
    )
    working_days = query.run()[0][0] or 0
    new_leaves = working_days // on_working_days

    return new_leaves


def allocate_leaves_for_worked_days():
    leave_types = get_wo_leaves()
    today = frappe.flags.current_date or getdate()

    for leave_type in leave_types:
        leave_allocations = get_leave_allocations(today, leave_type.name)
        for allocation in leave_allocations:
            if not allocation.leave_policy_assignment and not allocation.leave_policy:
                continue

            leave_policy = (
                allocation.leave_policy
                if allocation.leave_policy
                else frappe.db.get_value(
                    "Leave Policy Assignment", allocation.leave_policy_assignment, ["leave_policy"]
                )
            )

            annual_allocation = frappe.db.get_value(
                "Leave Policy Detail",
                filters={"parent": leave_policy, "leave_type": leave_type.name},
                fieldname=["annual_allocation"],
            )
            new_leaves = fetch_leaves_for_working_days(
                allocation.employee,
                allocation.from_date,
                allocation.to_date,
                leave_type.custom_number_of_working_days,
            )
            new_leaves_allocated = max(annual_allocation, new_leaves)
            allocation_doc = frappe.get_doc("Leave Allocation", allocation.name)
            allocation_doc.new_leaves_allocated = new_leaves_allocated
            allocation_doc.save()


def get_wo_leaves():
    return frappe.get_all(
        "Leave Type",
        fields=["*"],
        filters={"custom_calculate_based_on_working_days": 1},
    )
