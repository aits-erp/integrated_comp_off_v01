from collections import defaultdict
from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, get_datetime, get_time, getdate


def process():
    logs = frappe.get_all(
        "Bio Attendance Log",
        filters={"is_processed": "N"},
        fields=["*"],
        limit_page_length=5000,
        order_by="punch_datetime asc",
    )

    in_logs = [log for log in logs if log.punch_direction == "I"]
    out_logs = [log for log in logs if log.punch_direction == "O"]

    process_employee_checkin(in_logs)
    process_employee_checkout(out_logs)


def process_employee_checkin(logs):
    log_map = defaultdict(list)

    for log in logs:
        log_map[log["employee"]].append(log)
    checkins = dict(log_map)

    for emp, emp_logs in checkins.items():
        if not frappe.db.exists("Employee", emp):
            error_logs = []
            for log in emp_logs:
                checkin_doc = frappe.get_doc("Bio Attendance Log", log.name)
                checkin_doc.is_processed = "E"
                checkin_doc.message = f"Employee {emp} does not exist"
                error_logs.append(checkin_doc)

            # No need to trigger events for error logs
            frappe.db.bulk_update(error_logs)
            continue
        employee = frappe.get_doc("Employee", emp, for_update=False)
        shift_from_grade = frappe.db.get_values("Multiple Shifts", {"parent": employee.grade}, "shift", pluck="shift")

        for log in emp_logs:
            first_checkin_shift = get_first_checkin_for_the_day(emp, for_date=log.punch_date)
            # If we have a existing checkin, we don't need to calculate which shift to assign
            # Just use shift from last checkin
            if first_checkin_shift:
                shift_info = fetch_shift_details(first_checkin_shift, get_datetime(log.punch_datetime))
                shift_info = fetch_shift_details(first_checkin_shift, get_datetime(log.punch_datetime))
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": first_checkin_shift,
                        "log_type": "IN",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                        "shift_start": shift_info.start_datetime,
                        "shift_end": shift_info.end_datetime,
                        "shift_actual_start": shift_info.actual_start,
                        "shift_actual_end": shift_info.actual_end,
                    }
                )
                doc.flags.is_shift_fetch_required = False
                doc.insert()

            else:
                allowed_shifts = [employee.default_shift]
                allowed_shifts.extend(shift_from_grade)
                for_date = getdate(log.punch_date)
                assigned_shifts = frappe.get_all(
                    "Shift Assignment",
                    filters={
                        "employee": emp,
                        "start_date": ("<=", for_date),
                        "end_date": (">=", for_date),
                        "status": "Active",
                    },
                    pluck="shift_type",
                )
                allowed_shifts.extend(assigned_shifts)

                allowed_shifts = [x for x in allowed_shifts if x is not None]
                allowed_shifts = list(set(allowed_shifts))
                closest_shift = find_closest_shift_from_punch_time(allowed_shifts, log.punch_time)

                shift_info = fetch_shift_details(closest_shift, get_datetime(log.punch_datetime))
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": closest_shift,
                        "log_type": "IN",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                        "shift_start": shift_info.start_datetime,
                        "shift_end": shift_info.end_datetime,
                        "shift_actual_start": shift_info.actual_start,
                        "shift_actual_end": shift_info.actual_end,
                    }
                )
                doc.flags.is_shift_fetch_required = False
                doc.insert()

            log_doc = frappe.get_doc("Bio Attendance Log", log.name)
            log_doc.is_processed = "Y"
            log_doc.message = f"Checkin created for employee {emp}"
            log_doc.save()
            frappe.db.commit()


def process_employee_checkout(logs):
    log_map = defaultdict(list)

    for log in logs:
        log_map[log["employee"]].append(log)
    checkouts = dict(log_map)

    for emp, emp_logs in checkouts.items():
        if not frappe.db.exists("Employee", emp):
            error_logs = []
            for log in emp_logs:
                checkout_doc = frappe.get_doc("Bio Attendance Log", log.name)
                checkout_doc.is_processed = "E"
                checkout_doc.message = f"Employee {emp} does not exist"
                error_logs.append(checkout_doc)

            # No need to trigger events for error logs
            frappe.db.bulk_update(error_logs)
            continue
        employee = frappe.get_doc("Employee", emp, for_update=False)
        shift_from_grade = frappe.db.get_values("Multiple Shifts", {"parent": employee.grade}, "shift", pluck="shift")
        for log in emp_logs:
            first_checkin_shift = get_first_checkin_for_the_day(emp, for_date=log.punch_date, for_checkout=True)

            if first_checkin_shift:
                shift_info = fetch_shift_details(first_checkin_shift, get_datetime(log.punch_datetime))
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": first_checkin_shift,
                        "log_type": "OUT",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                        "shift_start": shift_info.start_datetime,
                        "shift_end": shift_info.end_datetime,
                        "shift_actual_start": shift_info.actual_start,
                        "shift_actual_end": shift_info.actual_end,
                    }
                )
                doc.flags.is_shift_fetch_required = False
                doc.insert()
                frappe.db.commit()
            else:
                allowed_shifts = [employee.default_shift]
                allowed_shifts.extend(shift_from_grade)
                for_date = getdate(log.punch_date)
                assigned_shifts = frappe.get_all(
                    "Shift Assignment",
                    filters={
                        "employee": emp,
                        "start_date": ("<=", for_date),
                        "end_date": (">=", for_date),
                        "status": "Active",
                    },
                    pluck="shift_type",
                )
                allowed_shifts.extend(assigned_shifts)

                allowed_shifts = [x for x in allowed_shifts if x is not None]
                allowed_shifts = list(set(allowed_shifts))
                closest_shift = find_closest_shift_from_punch_time(allowed_shifts, log.punch_time)

                shift_info = fetch_shift_details(closest_shift, get_datetime(log.punch_datetime))
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": closest_shift,
                        "log_type": "OUT",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                        "shift_start": shift_info.start_datetime,
                        "shift_end": shift_info.end_datetime,
                        "shift_actual_start": shift_info.actual_start,
                        "shift_actual_end": shift_info.actual_end,
                    }
                )
                doc.flags.is_shift_fetch_required = False
                doc.insert()
                frappe.db.commit()
            log_doc = frappe.get_doc("Bio Attendance Log", log.name)
            log_doc.is_processed = "Y"
            log_doc.message = f"Checkout created for employee {emp}"
            log_doc.save()


def find_closest_shift_from_punch_time(allowed_shifts: list[str], punch_time: str | timedelta):
    punch_time = get_datetime(punch_time)

    shifts = frappe.db.get_all("Shift Type", filters={"name": ["in", allowed_shifts]}, fields=["name", "start_time"])

    shift_timings = [
        {"name": s["name"], "start_time": get_datetime(s["start_time"])} for s in shifts if s["start_time"]
    ]

    closest_shift = min(shift_timings, key=lambda s: abs((punch_time - s["start_time"]).total_seconds()))

    return closest_shift["name"]


def get_first_checkin_for_the_day(employee: str, for_date, for_checkout=False):
    for_date = getdate(for_date)
    if for_checkout:
        start_time = get_datetime(add_days(for_date, -1))
        end_time = get_datetime(add_days(for_date, 1))
    else:
        start_time = get_datetime(for_date)
        end_time = get_datetime(add_days(for_date, 1))
    filters = [
        ["employee", "=", employee],
        ["log_type", "=", "IN"],
        ["time", ">=", start_time],
        ["time", "<", end_time],
    ]
    first_checkin_shift = frappe.db.get_value("Employee Checkin", filters, "shift", order_by="creation asc")

    return first_checkin_shift


def fetch_shift_details(shift_type: str, for_timestamp: datetime):
    from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_type

    if not shift_type:
        return frappe._dict()

    shift_type = get_shift_type(shift_type)
    start_datetime, end_datetime = get_shift_timings(shift_type, for_timestamp)

    actual_start = start_datetime - timedelta(minutes=shift_type.begin_check_in_before_shift_start_time)
    actual_end = end_datetime + timedelta(minutes=shift_type.allow_check_out_after_shift_end_time)

    return frappe._dict(
        {
            "shift_type": shift_type,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "actual_start": actual_start,
            "actual_end": actual_end,
        }
    )


def get_shift_timings(shift_type: dict, for_timestamp: datetime) -> tuple:
    start_time = shift_type.start_time
    end_time = shift_type.end_time

    # Compute margins
    shift_actual_start = get_time(
        datetime.combine(for_timestamp, datetime.min.time())
        + start_time
        - timedelta(minutes=shift_type.begin_check_in_before_shift_start_time)
    )
    shift_actual_end = get_time(
        datetime.combine(for_timestamp, datetime.min.time())
        + end_time
        + timedelta(minutes=shift_type.allow_check_out_after_shift_end_time)
    )

    for_time = get_time(for_timestamp.time())
    start_datetime = end_datetime = None

    # --- Case 1: Cross-day shift (e.g. 22:00 → 06:00)
    if start_time > end_time:
        if for_time >= shift_actual_start:
            # Timestamp is within same-day portion (e.g. 22:30)
            start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + start_time
            end_datetime = datetime.combine(for_timestamp + timedelta(days=1), datetime.min.time()) + end_time
        else:
            # Timestamp after midnight (e.g. 02:00 next day)
            start_datetime = datetime.combine(for_timestamp - timedelta(days=1), datetime.min.time()) + start_time
            end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + end_time

    # --- Case 2: Same-day shift but punch is after midnight (e.g. shift 11→18, checkout at 01:00)
    elif start_time < end_time and for_time < get_time(start_time):
        start_datetime = datetime.combine(for_timestamp - timedelta(days=1), datetime.min.time()) + start_time
        end_datetime = datetime.combine(for_timestamp - timedelta(days=1), datetime.min.time()) + end_time

    # --- Case 3: Margins that cross midnight (edge cases)
    elif (
        shift_actual_start > shift_actual_end
        and for_time < shift_actual_start
        and get_time(end_time) > shift_actual_end
    ):
        # After-midnight margin → belongs to previous day's shift
        for_timestamp -= timedelta(days=1)
        start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + start_time
        end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + end_time

    elif (
        shift_actual_start > shift_actual_end
        and for_time > shift_actual_end
        and get_time(start_time) < shift_actual_start
    ):
        # Before-midnight margin → belongs to next day's shift
        for_timestamp += timedelta(days=1)
        start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + start_time
        end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + end_time

    # --- Case 4: Regular same-day shift
    else:
        start_datetime = datetime.combine(for_timestamp, datetime.min.time()) + start_time
        end_datetime = datetime.combine(for_timestamp, datetime.min.time()) + end_time

    return start_datetime, end_datetime
