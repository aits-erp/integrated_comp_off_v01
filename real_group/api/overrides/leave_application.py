import datetime

import frappe
from frappe.utils import cint, date_diff, flt, getdate
from hrms.hr.doctype.leave_application.leave_application import get_holidays as _get_holidays

from real_group.utils import is_holiday_for_employee


@frappe.whitelist()
def get_holidays(employee, from_date, to_date, holiday_list=None):
    holidays = _get_holidays(employee, from_date, to_date, holiday_list)

    weekly_holiday_list = frappe.db.get_value("Employee", employee, "custom_weekly_holiday_list")

    weekly_holidays = frappe.db.count(
        "Weekly Off Holiday",
        {
            "parent": weekly_holiday_list,
            "holiday_date": ["between", [from_date, to_date]],
        },
    )
    return holidays + weekly_holidays


@frappe.whitelist()
def get_number_of_leave_days(
    employee: str,
    leave_type: str,
    from_date: datetime.date,
    to_date: datetime.date,
    half_day: int | str | None = None,
    half_day_date: datetime.date | str | None = None,
    holiday_list: str | None = None,
) -> float:
    """Returns number of leave days between 2 dates after considering half day and holidays
    (Based on the include_holiday setting in Leave Type)"""
    grade = frappe.db.get_value("Employee", employee, "grade")
    apply_sandwitch = frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag")

    number_of_days = 0
    if cint(half_day) == 1:
        if getdate(from_date) == getdate(to_date):
            number_of_days = 0.5
        elif half_day_date and getdate(from_date) <= getdate(half_day_date) <= getdate(to_date):
            number_of_days = date_diff(to_date, from_date) + 0.5
        else:
            number_of_days = date_diff(to_date, from_date) + 1
    else:
        number_of_days = date_diff(to_date, from_date) + 1

    if not apply_sandwitch:
        number_of_days = flt(number_of_days) - flt(
            get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        )
    else:
        holiday_on_from_date = is_holiday_for_employee(employee, from_date)
        holiday_on_to_date = is_holiday_for_employee(employee, to_date)
        if holiday_on_from_date and holiday_on_from_date.get("is_holiday"):
            number_of_days -= 1
        if holiday_on_to_date and holiday_on_to_date.get("is_holiday"):
            number_of_days -= 1
    if cint(half_day) == 1 and apply_sandwitch:
        number_of_days = flt(number_of_days) - flt(
            get_holidays(employee, from_date, to_date, holiday_list=holiday_list)
        )

    return number_of_days
