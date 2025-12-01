import frappe
from frappe.utils import add_days, date_diff, getdate

from real_group.utils import is_holiday_for_employee


def validate(doc, method=None):
    validate_change_request_day(doc)
    validate_cl(doc)
    validate_el_and_cl(doc)
    validate_compensation_leave(doc)
    validate_workflow_state(doc)
    validate_attendance(doc)
    validate_cross_month_leave(doc)


def on_update(doc, method=None):
    assign_leave(doc)


def before_cancel(doc, method=None):
    if frappe.db.exists(
        "Salary Slip",
        {
            "employee": doc.employee,
            "start_date": ["<=", doc.from_date],
            "end_date": [">=", doc.from_date],
            "docstatus": 1,
        },
    ):
        frappe.throw(frappe._("Cannot cancel: Salary for this period has already been submitted."))


def before_delete(doc, method=None):
    if frappe.db.exists(
        "Salary Slip",
        {
            "employee": doc.employee,
            "start_date": ["<=", doc.from_date],
            "end_date": [">=", doc.from_date],
            "docstatus": 1,
        },
    ):
        frappe.throw(frappe._("Cannot delete: Salary for this period has already been submitted."))


def validate_compensation_leave(doc):
    if (
        doc.leave_type
        and frappe.db.get_value("Leave Type", doc.leave_type, "is_compensatory")
        and doc.from_date != doc.to_date
    ):
        if not doc.compensatory_leave_application:
            frappe.throw(frappe._("You may apply for Compensatory Off Leave one day at a time!"))


def validate_workflow_state(doc):
    if doc.workflow_state in ("Rejected by HOD", "Rejected by HR", "Rejected at Gate") and (
        doc.custom_reason_for_rejection == "" or doc.custom_reason_for_rejection is None
    ):
        frappe.throw(frappe._("Kindly set the reason for rejection"))


def validate_attendance(doc):
    if doc.from_date == doc.to_date:
        att_exist = frappe.db.exists(
            "Attendance",
            {
                "employee": doc.employee,
                "attendance_date": doc.from_date,
                "status": "Present",
                "docstatus": ["!=", 2],
            },
        )
        if att_exist:
            frappe.throw(
                frappe._("Attendance is already marked for the Employee {0} on {1}").format(doc.employee, doc.from_date)
            )
    else:
        att_dates = []
        cur_date = doc.from_date
        while cur_date <= doc.to_date:
            att_dates.append(cur_date)
            cur_date = add_days(cur_date, days=1)
        for date in att_dates:
            att_exist = frappe.db.exists(
                "Attendance",
                {
                    "employee": doc.employee,
                    "attendance_date": date,
                    "status": "Present",
                    "docstatus": ["!=", 2],
                },
            )
            if att_exist:
                frappe.throw(
                    frappe._("Attendance is already marked for the Employee {0} on {1}").format(doc.employee, date)
                )


def validate_cross_month_leave(doc):
    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    if from_date.month != to_date.month or from_date.year != to_date.year:
        frappe.throw(frappe._("Leave application cannot span across multiple months."))


def assign_leave(doc):
    if doc.workflow_state in ("Pending at HOD"):
        approver = frappe.db.get_value("Employee", doc.employee, "reports_to")

        if not approver:
            frappe.throw(frappe._("No approver found for this employee."))

        assignment_exist = frappe.db.exists(
            "ToDo",
            {
                "status": "Open",
                "description": "Gate Pass Assignment",
                "reference_type": "Leave Application",
                "reference_name": doc.name,
                "allocated_to": approver,
            },
        )
        if not assignment_exist:
            assignment = frappe.get_doc(
                dict(
                    doctype="ToDo",
                    status="Open",
                    description="Gate Pass Assignment",
                    reference_type="Leave Application",
                    reference_name=doc.name,
                    allocated_to=approver,
                )
            )
            assignment.insert()

    elif doc.workflow_state in ("Pending at HR"):
        approver = frappe.db.get_value("Employee", doc.employee, "leave_approver")

        if not approver:
            frappe.throw(frappe._("No approver found for this employee."))

        assignment_exist = frappe.db.exists(
            "ToDo",
            {
                "status": "Open",
                "description": "Gate Pass Assignment",
                "reference_type": "Leave Application",
                "reference_name": doc.name,
                "allocated_to": approver,
            },
        )
        if not assignment_exist:
            assignment = frappe.get_doc(
                dict(
                    doctype="ToDo",
                    status="Open",
                    description="Gate Pass Assignment",
                    reference_type="Leave Application",
                    reference_name=doc.name,
                    allocated_to=approver,
                )
            )
            assignment.insert()

    if doc.workflow_state == "Gate Pass":
        approver = frappe.db.get_value("Employee", doc.employee, "custom_gate_pass_approver")
        if not approver:
            frappe.throw(frappe._("No gate pass approver found for this employee."))

        assignment_exist = frappe.db.exists(
            "ToDo",
            {
                "status": "Open",
                "description": "Gate Pass Assignment",
                "reference_type": "Leave Application",
                "reference_name": doc.name,
                "allocated_to": approver,
            },
        )
        if not assignment_exist:
            assignment = frappe.get_doc(
                dict(
                    doctype="ToDo",
                    status="Open",
                    description="Gate Pass Assignment",
                    reference_type="Leave Application",
                    reference_name=doc.name,
                    allocated_to=approver,
                )
            )
            assignment.insert()


def validate_cl(doc):
    leave_type = doc.leave_type
    is_based_on_working_days = frappe.db.get_value("Leave Type", leave_type, "custom_calculate_based_on_working_days")
    is_cl = "casual" in leave_type.lower()
    if not is_based_on_working_days and is_cl:
        prev_day = add_days(doc.from_date, -1)
        next_day = add_days(doc.to_date, 1)

        if is_holiday_for_employee(doc.employee, prev_day) or is_holiday_for_employee(doc.employee, next_day):
            frappe.throw(
                frappe._(
                    "Casual Leave cannot be applied before or after a holiday or weekly off. Please adjust your leave dates."
                )
            )


def validate_el_and_cl(doc):
    leave_type = doc.leave_type

    leave_type_lower = leave_type.lower()
    is_el = "earned" in leave_type_lower
    is_cl = "casual" in leave_type_lower

    if not (is_el or is_cl):
        return

    # Check for overlapping or adjacent leave applications
    overlapping_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": doc.employee,
            "docstatus": ["!=", 2],
            "name": ["!=", doc.name],
        },
        fields=["name", "leave_type", "from_date", "to_date", "half_day", "half_day_date"],
    )
    doc_from = getdate(doc.from_date)
    doc_to = getdate(doc.to_date)

    for leave in overlapping_leaves:
        other_type = leave.leave_type.lower()
        other_is_el = "earned" in other_type
        other_is_cl = "casual" in other_type

        # Only compare EL vs CL
        if (is_el and other_is_el) or (is_cl and other_is_cl):
            continue

        other_from = getdate(leave.from_date)
        other_to = getdate(leave.to_date)

        # ---- 1️⃣ SAME DATE (FULL-DAY OR HALF-DAY) ----
        # Case: Half-day on same date
        if doc.half_day and leave.half_day:
            if doc.half_day_date == leave.half_day_date:
                frappe.throw(
                    "EL and CL cannot be applied on the same date for different halves. "
                    "One Present day is mandatory between EL and CL."
                )

        # Case: full-day overlap or same single date
        if doc_from <= other_to and other_from <= doc_to:
            # Only treat it as violation if actual date intersection (not range overlap logic)
            # means one of the dates is exactly same
            if doc_from == other_from or doc_from == other_to or doc_to == other_from or doc_to == other_to:
                frappe.throw(
                    "EL and CL cannot be applied on the same date. One Present day is mandatory between EL and CL."
                )

        # ---- 2️⃣ ADJACENT (Continuation) ----
        if doc_from == add_days(other_to, 1) or doc_to == add_days(other_from, -1):
            frappe.throw("EL and CL cannot be applied in continuation. One Present day is mandatory between EL and CL.")


def validate_change_request_day(doc):
    roles = frappe.get_roles()
    if "HR Manager" in roles or "HR User" in roles or any("Payroll" in r for r in roles):
        return
    branch = frappe.get_value("Employee", doc.employee, "branch")
    allowed_days = frappe.get_value("Branch", branch, "custom_change_request")
    if not allowed_days:
        return

    diff = date_diff(getdate(), doc.from_date)
    if diff > allowed_days:
        frappe.throw(frappe._("You can only change attendance request within {0} days.").format(allowed_days))
