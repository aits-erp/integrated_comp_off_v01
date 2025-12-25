# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

from datetime import date
from importlib import import_module

from frappe.utils import getdate

from real_group.utils import is_holiday_for_employee

dw = import_module("real_group.real_group.report.[new]_day_wise_attendance.[new]_day_wise_attendance")
form = import_module("real_group.real_group.report.[new]_form_14.[new]_form_14")


def execute(filters=None):
    month = filters.get("month")
    year = int(filters.get("year"))
    dates = dw.get_dates(month, year)
    start_date, end_date = getdate(dates[0]), getdate(dates[-1])
    columns = build_columns()

    form_filters = dict(filters)
    form_filters.setdefault("processed_report", 1)
    _, raw_rows = form.execute(form_filters)

    first_half_rows = [row for row in (raw_rows or []) if row and row.get("sr")]
    employee_ids = [row.get("token_no") for row in first_half_rows if row.get("token_no")]
    request_map = dw.get_attendance_requests(employee_ids, start_date, end_date)

    result = []
    for row in first_half_rows:
        employee_id = row.get("token_no")
        od_total, tour_total = _compute_od_and_tour(employee_id, dates, request_map)

        result.append(
            {
                "employee": employee_id,
                "employee_name": row.get("employee_name"),
                "total_present": row.get("p") or 0.0,
                "total_absent": row.get("a") or 0.0,
                "total_earned_leave": row.get("el") or 0.0,
                "total_casual_leave": row.get("cl") or 0.0,
                "total_od": od_total,
                "total_tour": tour_total,
                "total_compensatory_off": row.get("co") or 0.0,
                "total_holiday_leave": row.get("ho") or 0.0,
                "total_wo": row.get("wo") or 0.0,
                "total_ttl": row.get("ttl") or 0.0,
                "total_monthly_hours": row.get("m") or 0.0,
            }
        )

    return columns, result


def build_columns():
    columns = [
        {"fieldname": "employee", "fieldtype": "Data", "label": "Employee UID"},
        {"fieldname": "employee_name", "fieldtype": "Data", "label": "Employee Name"},
        {"fieldname": "total_present", "fieldtype": "Float", "default": 0, "label": "P"},
        {"fieldname": "total_absent", "fieldtype": "Float", "default": 0, "label": "A"},
        {"fieldname": "total_earned_leave", "fieldtype": "Float", "default": 0, "label": "EL"},
        {"fieldname": "total_casual_leave", "fieldtype": "Float", "default": 0, "label": "CL"},
        {"fieldname": "total_od", "fieldtype": "Float", "default": 0, "label": "OD"},
        {"fieldname": "total_tour", "fieldtype": "Float", "default": 0, "label": "Tour"},
        {"fieldname": "total_compensatory_off", "fieldtype": "Float", "default": 0, "label": "CO"},
        {"fieldname": "total_holiday_leave", "fieldtype": "Float", "default": 0, "label": "HO"},
        {"fieldname": "total_wo", "fieldtype": "Float", "default": 0, "label": "WO"},
        {"fieldname": "total_ttl", "fieldtype": "Float", "default": 0, "label": "Paid Days"},
        {"fieldname": "total_monthly_hours", "fieldtype": "Float", "default": 0, "label": "Monthly Hours"},
    ]
    return columns


def _is_holiday(employee: str, target_date: date) -> bool:
    holiday_info = is_holiday_for_employee(employee, target_date)
    return bool(holiday_info.get("is_holiday")) if isinstance(holiday_info, dict) else False


def _get_request_day_value(request: dict) -> float:
    if request.get("half_day"):
        return 0.5
    return 1.0


def _compute_od_and_tour(employee: str, dates: list[date], request_map: dict) -> tuple[float, float]:
    od_total = 0.0
    tour_total = 0.0

    employee_requests = request_map.get(employee) or {}
    for target_date in dates:
        if _is_holiday(employee, target_date):
            continue

        requests_on_date = employee_requests.get(dw.format_date(target_date), [])
        for request in requests_on_date:
            reason = (request.get("reason") or "").strip().lower()
            if reason == "official":
                od_total += _get_request_day_value(request)
            elif reason == "tour":
                tour_total += _get_request_day_value(request)

    return od_total, tour_total
