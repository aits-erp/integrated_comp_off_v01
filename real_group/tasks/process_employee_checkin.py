import datetime
from collections import defaultdict

import frappe
from frappe.utils import add_days, get_datetime, getdate


def process():
    logs = frappe.get_all("Bio Attendance Log", filters={"is_processed": "N"}, fields=["*"], limit_page_length=5000)

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

        first_checkin_shift = get_first_checkin_for_the_day(emp)

        # If we have a existing checkin, we don't need to calculate which shift to assign
        # Just use shift from last checkin
        if first_checkin_shift:
            for log in emp_logs:
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": first_checkin_shift,
                        "log_type": "IN",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                    }
                )
                doc.insert()
        else:
            employee = frappe.get_doc("Employee", emp, for_update=False)
            shift_from_grade = frappe.db.get_values(
                "Multiple Shifts", {"parent": employee.grade}, "shift", pluck="shift"
            )

            for log in emp_logs:
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
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": closest_shift,
                        "log_type": "IN",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                    }
                )
                doc.insert()
        for log in emp_logs:
            log_doc = frappe.get_doc("Bio Attendance Log", log.name)
            log_doc.is_processed = "Y"
            log_doc.message = f"Checkin created for employee {emp}"
            log_doc.save()
        frappe.db.commit()  # nosemgrep Commit for every employee


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
        first_checkin_shift = get_first_checkin_for_the_day(emp)

        if first_checkin_shift:
            for log in emp_logs:
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": first_checkin_shift,
                        "log_type": "OUT",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                    }
                )
                doc.insert()
        else:
            employee = frappe.get_doc("Employee", emp, for_update=False)
            shift_from_grade = frappe.db.get_values(
                "Multiple Shifts", {"parent": employee.grade}, "shift", pluck="shift"
            )

            for log in emp_logs:
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
                doc = frappe.get_doc(
                    {
                        "doctype": "Employee Checkin",
                        "employee": emp,
                        "time": get_datetime(log.punch_datetime),
                        "shift": closest_shift,
                        "log_type": "OUT",
                        "custom_bio_log_id": log.name,
                        "device_id": log.terminal_id,
                    }
                )
                doc.insert()

        for log in emp_logs:
            log_doc = frappe.get_doc("Bio Attendance Log", log.name)
            log_doc.is_processed = "Y"
            log_doc.message = f"Checkout created for employee {emp}"
            log_doc.save()
        frappe.db.commit()  # nosemgrep Commit for every employee


def find_closest_shift_from_punch_time(allowed_shifts: list[str], punch_time: str | datetime.timedelta):
    punch_time = get_datetime(punch_time)

    shifts = frappe.db.get_values("Shift Type", {"name": ["in", allowed_shifts]}, "start_time", pluck="start_time")
    shift_timings = [get_datetime(shift) for shift in shifts if shift is not None]

    closest_shift = min(shift_timings, key=lambda s: abs((punch_time - s).total_seconds()))
    return closest_shift


def get_first_checkin_for_the_day(employee: str):
    filters = [
        ["employee", "=", employee],
        ["log_type", "=", "IN"],
        ["time", ">=", get_datetime(getdate())],
        ["time", "<", get_datetime(add_days(getdate(), 1))],
    ]
    first_checkin_shift = frappe.db.get_value("Employee Checkin", filters, "shift", order_by="creation desc")
    return first_checkin_shift
