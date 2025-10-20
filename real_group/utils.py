from datetime import time, timedelta

import frappe
from frappe.utils import get_time, getdate


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
            "is_weekly_holiday": False,
        }
        return data
    else:
        is_holiday = frappe.db.get_value(
            "Holiday",
            {
                "parent": weekly_holiday_list,
                "holiday_date": getdate(date),
                "parenttype": "Weekly Holiday List",
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
                "is_weekly_holiday": True,
            }
            return data

    return False
