import datetime

import frappe
from frappe.utils import add_days, cint, flt, getdate
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
    """
    Return number of leave days considering:
      - half days
      - full-day or half-day holidays
      - sandwich leave logic (only if enabled in Employee Grade)

    Rules:
    - Full-day holiday counted as leave only if it lies between *two full* leave days (sandwich).
    - Half-day holidays always count as 0.5 day unless sandwiched.
    - Half-day leave at either end breaks sandwich.
    - Holidays on from/to dates are excluded.
    """

    from_date = getdate(from_date)
    to_date = getdate(to_date)
    half_day_date = getdate(half_day_date) if half_day_date else None
    is_half_day = cint(half_day) == 1

    grade = frappe.db.get_value("Employee", employee, "grade")
    apply_sandwich = False
    if grade:
        apply_sandwich = frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag") == 1

    # Build date range
    all_dates = []
    current = from_date
    while current <= to_date:
        all_dates.append(current)
        current = add_days(current, 1)

    # Preload holiday info for all dates
    holiday_info = {}
    for d in all_dates:
        info = is_holiday_for_employee(employee, d) or {}
        holiday_info[d] = {
            "is_holiday": bool(info.get("is_holiday")),
            "is_half_day": bool(info.get("is_half_day")),
        }

    # Assign status per date
    status = {}
    for d in all_dates:
        if is_half_day and half_day_date == d:
            status[d] = "half_leave"
        elif holiday_info[d]["is_holiday"]:
            status[d] = "half_holiday" if holiday_info[d]["is_half_day"] else "full_holiday"
        else:
            status[d] = "full_leave"

    # Holidays on start or end are never counted in sandwich
    if status.get(from_date, "").startswith("full_holiday"):
        status[from_date] = "excluded"
    if status.get(to_date, "").startswith("full_holiday"):
        status[to_date] = "excluded"

    total = 0.0
    i = 0
    n = len(all_dates)

    while i < n:
        current_date = all_dates[i]
        current_status = status[current_date]

        # --- FULL LEAVE ---
        if current_status == "full_leave":
            total += 1
            i += 1
            continue

        # --- HALF LEAVE ---
        if current_status == "half_leave":
            total += 0.5
            i += 1
            continue

        # --- HALF HOLIDAY ---
        if current_status == "half_holiday":
            total += 0.5  # always counts half
            i += 1
            continue

        # --- FULL HOLIDAY(S) BLOCK ---
        if current_status == "full_holiday":
            block_start = i
            while i < n and status[all_dates[i]] == "full_holiday":
                i += 1
            block_end = i - 1

            # Get previous and next dates
            prev_date = add_days(all_dates[block_start], -1)
            next_date = add_days(all_dates[block_end], 1)

            prev_full = prev_date in status and status[prev_date] == "full_leave"
            next_full = next_date in status and status[next_date] == "full_leave"
            if apply_sandwich and prev_full and next_full:
                total += block_end - block_start + 1
            continue

        # --- EXCLUDED HOLIDAYS ---
        i += 1

    return flt(total)
