import frappe
from frappe.utils import add_days, date_diff, get_first_day, get_last_day


def validate(doc, method=None):
    if doc.reason == "Personal" and doc.custom_to_time is None and doc.custom_from_time is None:
        frappe.throw(frappe._("kindly Set the from time and to time"))

    validate_single_day_request(doc)
    validate_multi_day_request(doc)
    validate_short_leave_request(doc)

    if doc.reason == "Mis Punch":
        if doc.from_date != doc.to_date:
            frappe.throw(frappe._("Attendance Request for Mis Punch can be marked for single day only!!"))


def before_insert(doc, method=None):
    from frappe.desk.doctype.bulk_update.bulk_update import submit_cancel_or_update_docs

    start_date = doc.from_date
    end_date = doc.to_date

    names = frappe.db.get_values(
        "Attendance Request",
        {
            "employee": doc.employee,
            "from_date": [">=", start_date],
            "to_date": ["<=", end_date],
            "docstatus": ["!=", 2],
        },
        fieldname="name",
        pluck=True,
    )
    if names:
        submit_cancel_or_update_docs("Attendance Request", names, "cancel")


def before_cancel(doc, method=None):
    if is_salary_processed(doc):
        frappe.throw(frappe._("Cannot cancel: Salary for this period has already been submitted."))


def before_delete(doc, method=None):
    if is_salary_processed(doc):
        frappe.throw(frappe._("Cannot delete: Salary for this period has already been submitted."))


def is_salary_processed(doc):
    if frappe.db.exists(
        "Salary Slip",
        {
            "employee": doc.employee,
            "start_date": ["<=", doc.from_date],
            "end_date": [">=", doc.from_date],
            "docstatus": 1,
        },
    ):
        return True
    return False


def validate_short_leave_request(doc):
    grade = frappe.get_cached_value("Employee", doc.employee, "grade")
    grade = frappe.get_cached_doc("Employee Grade", grade)

    from_date = get_first_day(doc.from_date)
    to_date = get_last_day(doc.from_date)

    if not (grade.custom_hours_per_leave) and doc.reason == "Personal":
        frappe.throw(frappe._("Not Eligible for short leave, kindly avail Short Leave on Employee Grade"))

    diff = doc.custom_to_time - doc.custom_from_time
    if grade.custom_hours_per_leave:
        if diff > grade.custom_hours_per_leave and doc.reason == grade.custom_short_leave_type:
            frappe.throw(frappe._("Attendance Request is not allowed beyond Short Leave Time Allowed "))

    if (
        frappe.db.count(
            "Attendance Request",
            {
                "employee": doc.employee,
                "from_date": [">=", from_date],
                "to_date": ["<=", to_date],
                "docstatus": ["!=", 2],
                "name": ["!=", doc.name],
            },
        )
        >= grade.custom_number_of_leaves
        and doc.reason == "Personal"
    ):
        frappe.throw(frappe._("Short Leave Limit Exceeded, Contact your HR Manager"))


def validate_single_day_request(doc):
    if date_diff(doc.to_date, doc.from_date) > 0:
        return

    if frappe.db.exists(
        "Attendance",
        {
            "employee": doc.employee,
            "attendance_date": doc.from_date,
            "status": "Present",
            "docstatus": ["!=", 2],
        },
    ):
        frappe.throw(frappe._("Attendance is already marked for the Employee {0}").format(doc.employee))


def validate_multi_day_request(doc):
    if date_diff(doc.to_date, doc.from_date) < 1:
        return

    start_date = doc.from_date
    end_date = doc.to_date
    range = []
    while start_date <= end_date:
        range.append(start_date)
        start_date = add_days(start_date, 1)

    if frappe.db.exists(
        "Attendance",
        {
            "employee": doc.employee,
            "attendance_date": ["in", range],
            "status": "Present",
            "docstatus": ["!=", 2],
        },
    ):
        frappe.throw(frappe._("Attendance is already marked for the Employee {0}").format(doc.employee))
