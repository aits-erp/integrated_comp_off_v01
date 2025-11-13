import frappe
from frappe.utils import get_timedelta

from real_group.tasks.process_employee_checkin import get_employee_allowed_shifts


@frappe.whitelist()
def get_leave_on_dates(employee, from_date, to_date):
    leave_on_dates = frappe.db.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "docstatus": ["!=", 2],
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date],
        },
        fields=["name", "from_date", "to_date", "half_day", "half_day_date", "status"],
    )
    return leave_on_dates


@frappe.whitelist()
def closest_shift_for_time(time: str, date: str, employee: str):
    time = get_timedelta(time)
    shifts = get_employee_allowed_shifts(employee, date)
    all_shifts = frappe.get_all(
        "Shift Type",
        filters={"name": ["in", shifts]},
        fields=["name", "start_time"],
    )
    for shift in all_shifts:
        shift["start_time"] = get_timedelta(shift["start_time"])
    closest_shift = min(all_shifts, key=lambda x: abs(x["start_time"] - time))

    return closest_shift.name
