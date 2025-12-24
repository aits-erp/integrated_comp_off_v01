import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, formatdate, get_link_to_form, getdate

from real_group.utils import is_holiday_for_employee


def validate(doc, method=None):
    validate_change_request_day(doc)
    validate_cl(doc)
    validate_el_and_cl(doc)
    validate_el_cl_gap_non_working_day(doc)
    validate_compensation_leave(doc)
    validate_workflow_state(doc)
    validate_attendance(doc)
    validate_cross_month_leave(doc)
    validate_attendance_request(doc)
    validate_leave_overlap(doc)


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
                frappe._("Attendance is already marked for the Employee {0} on {1}").format(
                    doc.employee, format_display_date(doc.from_date)
                )
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
                    frappe._("Attendance is already marked for the Employee {0} on {1}").format(
                        doc.employee, format_display_date(date)
                    )
                )


def validate_cross_month_leave(doc):
    from_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    if from_date.month != to_date.month or from_date.year != to_date.year:
        frappe.throw(frappe._("Leave application cannot span across multiple months."))


def validate_cl(doc):
    leave_type = doc.leave_type
    is_based_on_working_days = frappe.db.get_value(
        "Leave Type", leave_type, "custom_restrict_leave_adjacent_to_holiday"
    )
    if is_based_on_working_days:
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
            "from_date": ["<=", doc.from_date],
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
                    _(
                        "EL and CL cannot be applied on the same date for different half. "
                        "One Present day is mandatory between EL and CL."
                    )
                )

        # Case: full-day overlap or same single date
        if doc_from <= other_to and other_from <= doc_to:
            # Only treat it as violation if actual date intersection (not range overlap logic)
            # means one of the dates is exactly same
            if doc_from == other_from or doc_from == other_to or doc_to == other_from or doc_to == other_to:
                frappe.throw(
                    _("EL and CL cannot be applied on the same date. One Present day is mandatory between EL and CL.")
                )

        # ---- 2️⃣ ADJACENT (Continuation) ----
        earlier_end = min(doc_to, other_to)
        later_start = max(doc_from, other_from)

        if (other_is_cl or other_is_el) and not has_present_day_between(doc.employee, earlier_end, later_start):
            frappe.throw(
                _(
                    "EL and CL cannot be applied. One Present day is mandatory between EL and CL from {0} to {1}.".format(
                        format_display_date(earlier_end), format_display_date(later_start)
                    )
                )
            )


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


def validate_el_cl_gap_non_working_day(doc):
    leave_type = (doc.leave_type or "").lower()
    is_el = "earned" in leave_type
    is_cl = "casual" in leave_type

    if not (is_el or is_cl):
        return

    opposite_leaves = frappe.get_all(
        "Leave Application",
        filters={
            "employee": doc.employee,
            "docstatus": ["!=", 2],
            "name": ["!=", doc.name],
        },
        fields=["leave_type", "from_date", "to_date"],
    )

    doc_from = getdate(doc.from_date)
    doc_to = getdate(doc.to_date)

    for leave in opposite_leaves:
        other_type = (leave.leave_type or "").lower()
        other_is_el = "earned" in other_type
        other_is_cl = "casual" in other_type

        # Only EL ↔ CL comparison
        if is_el and not other_is_cl:
            continue
        if is_cl and not other_is_el:
            continue

        other_from = getdate(leave.from_date)
        other_to = getdate(leave.to_date)

        gap_date = None

        # Doc AFTER other
        if doc_from > other_to:
            if date_diff(doc_from, other_to) == 2:
                gap_date = add_days(other_to, 1)

        # Doc BEFORE other
        elif other_from > doc_to:
            if date_diff(other_from, doc_to) == 2:
                gap_date = add_days(doc_to, 1)

        # Only validate EXACT one-day gap
        if not gap_date:
            continue

        reason = get_non_working_gap_reason(doc.employee, gap_date)
        if reason:
            frappe.throw(frappe._("EL and CL must be separated by a Present working day. {0}").format(reason))


def format_display_date(value):
    if not value:
        return ""
    return formatdate(value, "dd-MM-yyyy")


def get_non_working_gap_reason(employee, gap_date):
    attendance_status = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": gap_date,
            "docstatus": ["!=", 2],
        },
        "status",
    )

    if attendance_status in ("Absent", "Half Day"):
        return frappe._("Attendance on {0} is marked {1}.").format(format_display_date(gap_date), attendance_status)

    holiday = is_holiday_for_employee(employee, gap_date)
    if holiday:
        if holiday.get("is_weekly_off"):
            return frappe._("{0} is a Weekly Off.").format(format_display_date(gap_date))
        return frappe._("{0} is a Holiday.").format(format_display_date(gap_date))

    return None


def validate_attendance_request(doc):
    requests = frappe.get_all(
        "Attendance Request",
        filters={
            "employee": doc.employee,
            "from_date": ["<=", doc.to_date],
            "to_date": [">=", doc.from_date],
            "docstatus": ["!=", 2],
            "workflow_state": ["not in", ["Rejected", "Cancelled", "Reject by HOD", "Reject by HR", "Reject at Gate"]],
        },
        fields=["name", "from_date", "to_date", "half_day_date", "custom_half_type", "half_day"],
    )

    if requests:
        for r in requests:
            # Full-day attendance exists
            if not r.half_day:
                frappe.throw(
                    _("Attendance Request {0} exists for the selected date range. Cannot apply leave.").format(
                        get_link_to_form("Attendance Request", r.name)
                    )
                )

            # Half-day attendance exists
            if r.half_day:
                # Half-day conflict
                if (
                    r.half_day_date
                    and doc.half_day_date
                    and getdate(r.half_day_date) == getdate(doc.half_day_date)
                    and r.custom_half_type == doc.custom_half_type
                ):
                    frappe.throw(
                        _("Attendance Request {0} exists for the selected half day. Cannot apply leave.").format(
                            get_link_to_form("Attendance Request", r.name)
                        )
                    )

                # Full-day leave conflicts with existing half-day attendance
                if not getattr(doc, "half_day", False) and r.half_day_date:
                    if getdate(doc.from_date) <= getdate(r.half_day_date) <= getdate(doc.to_date):
                        frappe.throw(
                            _(
                                "Attendance Request {0} already exists for a half day within this range. Full-day leave cannot be applied."
                            ).format(get_link_to_form("Attendance Request", r.name))
                        )


def validate_leave_overlap(self):
    # 1. Prepare to fetch overlapping requests
    if not self.name:
        self.name = "New Leave Application"

    requests = frappe.get_all(
        "Leave Application",
        filters={
            "employee": self.employee,
            "from_date": ["<=", self.to_date],
            "to_date": [">=", self.from_date],
            "docstatus": ["!=", 2],
            "name": ["!=", self.name],
        },
        fields=["name", "from_date", "to_date", "half_day_date", "custom_half_type", "half_day", "leave_type"],
    )

    if requests:
        for r in requests:
            if not cint(r.half_day):
                self.throw_overlap_error(r)

            elif cint(r.half_day):
                is_same_date = (
                    r.half_day_date and self.half_day_date and getdate(r.half_day_date) == getdate(self.half_day_date)
                )

                if is_same_date and r.custom_half_type == self.custom_half_type:
                    self.throw_overlap_error(r)

                elif is_same_date and r.custom_half_type != self.custom_half_type:
                    continue

                if not cint(self.half_day) and r.half_day_date:
                    if getdate(self.from_date) <= getdate(r.half_day_date) <= getdate(self.to_date):
                        self.throw_overlap_error(r)


def throw_overlap_error(self, d):
    # Use the existing error function from Leave Application Doctype
    form_link = get_link_to_form("Leave Application", d.name)
    msg = _("Employee {0} has already applied for {1} between {2} and {3} : {4}").format(
        self.employee, d["leave_type"], formatdate(d["from_date"]), formatdate(d["to_date"]), form_link
    )
    frappe.throw(msg, OverlapError)


def has_present_day_between(employee, start_date, end_date):
    """
    Returns True if employee has at least one Attendance
    with status = 'Present' between start_date and end_date (exclusive).
    """
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    _filter_dates = []
    while start_date <= end_date:
        if is_holiday_for_employee(employee, start_date):
            start_date = add_days(start_date, 1)
            continue
        _filter_dates.append(start_date)
        start_date = add_days(start_date, 1)

    return bool(
        frappe.db.exists(
            "Attendance",
            {
                "employee": employee,
                "attendance_date": ["in", _filter_dates],
                "status": "Present",
                "docstatus": 1,
            },
        )
    )


class OverlapError(frappe.ValidationError):
    pass
