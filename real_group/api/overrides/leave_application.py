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
      - holidays
      - sandwich leave logic

    Rules:
    - Holiday counted as leave only if it lies between *two full* leave days.
    - Half-day at either end breaks sandwich.
    - Holidays on from/to dates are excluded.
    - Consecutive holidays handled as one block.
    """
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    half_day_date = getdate(half_day_date) if half_day_date else None
    is_half_day = cint(half_day) == 1

    # Build date range
    all_dates = []
    current = from_date
    while current <= to_date:
        all_dates.append(current)
        current = add_days(current, 1)

    # Preload holidays for all dates in one go
    holiday_flags = {}
    for d in all_dates:
        info = is_holiday_for_employee(employee, d) or {}
        holiday_flags[d] = bool(info.get("is_holiday"))

    # Assign status per date
    status = {}
    for d in all_dates:
        if is_half_day and half_day_date == d:
            status[d] = "half"
        elif holiday_flags.get(d):
            status[d] = "holiday"
        else:
            status[d] = "full"

    # Holidays on start or end are never counted
    if status.get(from_date) == "holiday":
        status[from_date] = "excluded"
    if status.get(to_date) == "holiday":
        status[to_date] = "excluded"

    total = 0.0
    i = 0
    n = len(all_dates)

    while i < n:
        current_date = all_dates[i]
        current_status = status[current_date]

        # --- FULL LEAVE ---
        if current_status == "full":
            total += 1
            i += 1
            continue

        # --- HALF LEAVE ---
        if current_status == "half":
            total += 0.5
            i += 1
            continue

        # --- HOLIDAY(S) BLOCK ---
        if current_status == "holiday":
            block_start = i
            while i < n and status[all_dates[i]] == "holiday":
                i += 1
            block_end = i - 1

            # Get previous and next dates
            prev_date = add_days(all_dates[block_start], -1)
            next_date = add_days(all_dates[block_end], 1)

            prev_full = prev_date in status and status[prev_date] == "full"
            next_full = next_date in status and status[next_date] == "full"

            # Only count block if *both* sides are full leaves
            if prev_full and next_full:
                total += block_end - block_start + 1
            continue

        # --- EXCLUDED HOLIDAYS ---
        i += 1

    return flt(total)
