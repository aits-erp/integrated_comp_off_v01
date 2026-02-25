import frappe
from frappe import _
from frappe.utils import date_diff, get_link_to_form, getdate

from real_group.utils import SandwichPolicyError


# ---------------------------------------------------------
# Main hooks
# ---------------------------------------------------------


def validate(doc, method=None):
    validate_zero_punch_employee(doc)
    validate_change_request_day(doc)
    validate_date(doc)
    validate_attendance(doc)

    if doc.reason == "Mis Punch":
        if getdate(doc.from_date) != getdate(doc.to_date):
            frappe.throw(
                _(
                    "Attendance Request for Mis Punch can be marked for single day only!!"
                )
            )


def before_cancel(doc, method=None):
    if is_salary_processed(doc):
        frappe.throw(
            _("Cannot cancel: Salary for this period has already been submitted."),
            SandwichPolicyError,
        )


def before_delete(doc, method=None):
    if is_salary_processed(doc):
        frappe.throw(
            _("Cannot delete: Salary for this period has already been submitted.")
        )


def on_submit(doc, method=None):
    doc.status = "Approved"


def on_cancel(doc, method=None):
    doc.status = "Cancelled"


# ---------------------------------------------------------
# Validations
# ---------------------------------------------------------


def validate_zero_punch_employee(doc):
    grade = frappe.get_value("Employee", doc.employee, "grade")
    is_zero_punch = frappe.get_value(
        "Employee Grade", grade, "custom_no_punch_applicable"
    )

    if is_zero_punch:
        frappe.throw(_("Attendance Request cannot be created for Zero Punch Employee"))


def validate_attendance(doc):
    """
    Attendance Request is allowed to override attendance.
    Old logic blocking on existing attendance is intentionally removed.

    Actual overwrite should happen in submit logic
    (cancel + recreate attendance rows).
    """
    if frappe.flags.in_reprocess_attendance:
        return
    return


def validate_date(doc):

    # -------------------- Leave overlap --------------------

    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": doc.employee,
            "from_date": ["<=", doc.to_date],
            "to_date": [">=", doc.from_date],
            "docstatus": ["!=", 2],
            "workflow_state": [
                "not in",
                [
                    "Rejected",
                    "Cancelled",
                    "Reject by HOD",
                    "Reject by HR",
                    "Reject at Gate",
                ],
            ],
        },
        fields=[
            "name",
            "half_day_date",
            "custom_half_type",
            "half_day",
            "from_date",
            "to_date",
        ],
    )

    for l in leaves:

        if not l.half_day:
            frappe.throw(
                _(
                    "Leave Application {0} exists for the selected date range. Attendance Request cannot be processed."
                ).format(get_link_to_form("Leave Application", l.name))
            )

        if l.half_day:

            if (
                l.half_day_date
                and doc.half_day_date
                and getdate(l.half_day_date) == getdate(doc.half_day_date)
                and l.custom_half_type == doc.custom_half_type
            ):
                frappe.throw(
                    _(
                        "Leave Application {0} exists for the selected half day. Attendance Request cannot be processed."
                    ).format(get_link_to_form("Leave Application", l.name))
                )

            if not getattr(doc, "half_day", False) and l.half_day_date:
                if (
                    getdate(doc.from_date)
                    <= getdate(l.half_day_date)
                    <= getdate(doc.to_date)
                ):
                    frappe.throw(
                        _(
                            "Leave Application {0} already exists for a half day within this date range. Full-day Attendance Request cannot be processed."
                        ).format(get_link_to_form("Leave Application", l.name))
                    )

    # -------------------- Attendance Request overlap --------------------

    requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": doc.employee,
            "from_date": ["<=", doc.to_date],
            "to_date": [">=", doc.from_date],
            "docstatus": ["!=", 2],
            "name": ["!=", doc.name],
            "workflow_state": [
                "not in",
                [
                    "Rejected",
                    "Cancelled",
                    "Reject by HOD",
                    "Reject by HR",
                    "Reject at Gate",
                ],
            ],
        },
        fields=[
            "name",
            "from_date",
            "to_date",
            "half_day_date",
            "custom_half_type",
            "half_day",
        ],
    )

    for r in requests:

        if not r.half_day:
            frappe.throw(
                _(
                    "Attendance Request {0} exists for the selected date range. Attendance Request cannot be processed."
                ).format(get_link_to_form("Attendance Request", r.name))
            )

        if r.half_day:

            if (
                r.half_day_date
                and doc.half_day_date
                and getdate(r.half_day_date) == getdate(doc.half_day_date)
                and r.custom_half_type == doc.custom_half_type
            ):
                frappe.throw(
                    _(
                        "Attendance Request {0} exists for the selected half day. Attendance Request cannot be processed."
                    ).format(get_link_to_form("Attendance Request", r.name))
                )

            if not getattr(doc, "half_day", False) and r.half_day_date:
                if (
                    getdate(doc.from_date)
                    <= getdate(r.half_day_date)
                    <= getdate(doc.to_date)
                ):
                    frappe.throw(
                        _(
                            "Attendance Request {0} already exists for a half day within this date range. Full-day Attendance Request cannot be processed."
                        ).format(get_link_to_form("Attendance Request", r.name))
                    )


def validate_change_request_day(doc):

    roles = frappe.get_roles()

    if (
        "HR Manager" in roles
        or "HR User" in roles
        or any("Payroll" in r for r in roles)
    ):
        return

    branch = frappe.get_value("Employee", doc.employee, "branch")
    allowed_days = frappe.get_value("Branch", branch, "custom_change_request")

    if not allowed_days:
        return

    diff = date_diff(getdate(), doc.from_date)

    if diff > allowed_days:
        frappe.throw(
            _("You can only change attendance request within {0} days.").format(
                allowed_days
            )
        )


# ---------------------------------------------------------
# Salary lock
# ---------------------------------------------------------


def is_salary_processed(doc):

    return bool(
        frappe.db.exists(
            "Salary Slip",
            {
                "employee": doc.employee,
                "start_date": ["<=", doc.from_date],
                "end_date": [">=", doc.from_date],
                "docstatus": 1,
            },
        )
    )
