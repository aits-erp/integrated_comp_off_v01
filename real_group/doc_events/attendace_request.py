import frappe
from frappe.utils import add_days, date_diff, getdate


def validate(doc, method=None):
    validate_change_request_day(doc)
    validate_attendance(doc)

    if doc.reason == "Mis Punch":
        if getdate(doc.from_date) != getdate(doc.to_date):
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


def on_submit(doc, method=None):
    doc.status = "Approved"


def on_cancel(doc, method=None):
    doc.status = "Cancelled"


def cancel_short_leaves(doc):
    attendance = frappe.db.exists(
        "Attendance",
        {
            "date": ["between", [doc.from_date, doc.to_date]],
            "employee": doc.employee,
            "status": ["in", ["Present", "Absent", "Half Day"]],
        },
    )
    if attendance:
        frappe.throw(frappe._("Attendance is already marked for the selected dates."))
    else:
        short_leaves = frappe.get_all(
            "Short Leave",
            filters={
                "employee": doc.employee,
                "for_date": ["between", [doc.from_date, doc.to_date]],
                "docstatus": 1,
            },
            pluck="name",
        )
        for sl in short_leaves:
            sl_doc = frappe.get_doc("Short Leave", sl)
            sl_doc.cancel()


def validate_attendance(doc):
    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    range = []
    while from_date <= to_date:
        range.append(from_date)
        from_date = add_days(from_date, 1)

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


def validate_change_request_day(doc):
    branch = frappe.get_value("Employee", doc.employee, "branch")
    allowed_days = frappe.get_value("Branch", branch, "custom_change_request")
    if not allowed_days:
        return

    diff = date_diff(getdate(), doc.from_date)
    if diff > allowed_days:
        frappe.throw(frappe._("You can only change attendance request within {0} days.").format(allowed_days))


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
