import json

import frappe
from frappe.integrations.utils import make_get_request
from frappe.utils import get_datetime, getdate

from real_group.tasks.process_employee_checkin import fetch_shift_details


def after_insert(doc, method=None):
    pass


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
        employee_grade.custom_single_punch_applicable or employee_grade.custom_double_punch_applicable
    ):
        return

    for_date = getdate(doc.time)
    is_first_checkin = frappe.db.count(
        "Employee Checkin",
        {"employee": doc.employee, "log_type": "IN", "time": ["Between", [for_date, for_date]]},
    )
    if is_first_checkin > 1:
        return

    shift_start_time = doc.shift_actual_start

    if not shift_start_time:
        data = fetch_shift_details(doc.employee, doc.time, employee.grade)
        shift_start_time = data.get("actual_start")

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


def get_sms_creds():
    setup = frappe.local.conf.get("sms_integration", {})
    if not setup:
        return None
    return setup
