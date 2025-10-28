import json

import frappe
from frappe.integrations.utils import make_get_request
from frappe.utils import get_datetime, get_timedelta, getdate

from real_group.tasks.process_employee_checkin import fetch_shift_details


def validate(doc, method=None):
    doc.custom_processed_time = doc.time
    update_processed_time(doc)


def before_insert(doc, method=None):
    apply_short_leave_attendance_on_late_checkin(doc)


def after_insert(doc, method=None):
    send_sms_on_late_checkin(doc)


def update_processed_time(doc):
    if not is_first_checkin(doc) or doc.log_type != "IN":
        return

    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    data = fetch_shift_details(doc.shift, doc.time, employee.grade)
    shift_start_time = data.get("actual_start")

    start_time = get_datetime(shift_start_time)
    checkin_time = get_datetime(doc.time)

    if checkin_time < start_time:
        doc.custom_processed_time = start_time


def apply_short_leave_attendance_on_late_checkin(doc):
    if not is_first_checkin(doc) or doc.log_type != "IN":
        return
    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    grade = frappe.get_cached_doc("Employee Grade", employee.grade, for_update=False)

    if (
        grade.custom_short_leave_type != "Personal"
        or not grade.custom_number_of_leaves
        or not grade.custom_hours_per_leave
    ):
        return

    data = fetch_shift_details(doc.shift, doc.time, employee.grade)
    shift_start_time = data.get("start_datetime")

    start_time = get_datetime(shift_start_time)
    checkin_time = get_datetime(doc.time)
    diff = checkin_time - start_time

    if get_timedelta() < diff < grade.custom_hours_per_leave:
        try:
            short_leave = frappe.get_doc(
                {
                    "doctype": "Short Leave",
                    "employee": doc.employee,
                    "for_date": getdate(doc.time),
                    "shift": doc.shift,
                    "shift_start_time": start_time,
                    "punch_time": checkin_time,
                }
            )
            short_leave.insert(ignore_permissions=True)
            short_leave.submit()
            short_leave.add_tag("Auto Created on Late Checkin")
            minutes = int(diff.total_seconds() / 60)
            short_leave.add_comment(text=f"Created automatically for late check-in: {minutes} minutes late")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Auto Attendance Request Creation Failed")


def send_sms_on_late_checkin(doc):
    if doc.log_type != "IN":
        return

    sms_gateway = get_sms_creds()
    if not sms_gateway:
        return

    url = sms_gateway.get("url")
    api_key = sms_gateway.get("api_key")
    sender_id = sms_gateway.get("sender_id")

    if not url or not api_key or not sender_id:
        return

    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    employee_grade = frappe.get_cached_doc("Employee Grade", employee.grade, for_update=False)
    if not employee.cell_number or (
        employee_grade.custom_single_punch_applicable or employee_grade.custom_no_punch_applicable
    ):
        return

    if not is_first_checkin(doc):
        return

    shift_start_time = doc.shift_start

    if not shift_start_time:
        data = fetch_shift_details(doc.shift, doc.time, employee.grade)
        shift_start_time = data.get("start_datetime")

    if not shift_start_time:
        return
    shift_start_time = get_datetime(shift_start_time)
    checkin_time = get_datetime(doc.time)

    if shift_start_time > checkin_time:
        return

    difference_in_minutes = (checkin_time - shift_start_time).total_seconds() / 60

    message = (
        f"Hello {doc.employee_name},%0A%0A"
        f"You have arrived {difference_in_minutes} minutes late at work today.%0A"
        f"Your clock-in time is {doc.time}.%0A%0A"
        f"Regards,%0A"
        f"REAL Group"
    )

    url = f"{url}?apikey={api_key}&senderid={sender_id}&number={employee.cell_number}&message={message}"

    sms_response = make_get_request(url)
    sms_response_log = frappe.new_doc("SMS Response Log")
    sms_response_log.response = json.dumps(sms_response)
    sms_response_log.checkin = doc.name
    sms_response_log.save()


def is_first_checkin(doc):
    for_date = getdate(doc.time)
    return (
        frappe.db.count(
            "Employee Checkin",
            {"employee": doc.employee, "log_type": "IN", "time": ["Between", [for_date, for_date]]},
        )
        < 2
    )


def get_sms_creds():
    setup = frappe.local.conf.get("sms_integration", {})
    if not setup:
        return None
    return setup
