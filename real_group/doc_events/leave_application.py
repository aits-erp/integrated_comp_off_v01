import frappe
from frappe.utils import add_days, getdate


def validate(doc, method=None):
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
