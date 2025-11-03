from datetime import timedelta

import frappe
from frappe.utils import add_days, date_diff, get_first_day, get_last_day, getdate

from real_group.utils import convert_time_to_hours, is_holiday_for_employee


def validate(doc, method=None):
    doc.custom_working_hours = None
    if doc.working_hours and doc.working_hours > 0:
        total_seconds = round(doc.working_hours * 3600 / 60) * 60
        doc.custom_working_hours = timedelta(seconds=total_seconds)
    else:
        doc.custom_working_hours = None


def on_submit(doc, method=None):
    update_attendance_tag(doc)
    frappe.enqueue(allocate_c_off, doc=doc, queue="long", enqueue_after_commit=True)
    frappe.enqueue(allocate_incentive, doc=doc, queue="long", enqueue_after_commit=True)


def update_attendance_tag(doc):
    status = ""

    is_holiday = is_holiday_for_employee(doc.employee, doc.attendance_date)
    grade = frappe.get_value("Employee", doc.employee, "grade")
    is_sandwich = frappe.db.get_value("Employee Grade", grade, "custom_sandwich_flag")
    if doc.status == "On Leave":
        leave_type = frappe.get_doc("Leave Type", doc.leave_type)
        if is_sandwich and is_holiday and is_holiday.get("is_holiday"):
            status = "A"
        elif leave_type.is_lwp:
            status = "LWP"
        elif leave_type.is_earned_leave:
            status = "EL"
        elif "Casual Leave" in leave_type.name:
            status = "CL"
        elif leave_type.is_compensatory:
            status = "CO"

    elif doc.status == "Present" and not is_holiday:
        status = "P"
    elif doc.status == "Half Day":
        status = "HD"
    elif doc.status == "Absent":
        status = "A"
    elif is_holiday and is_holiday.get("is_holiday"):
        checkins = frappe.db.exists("Employee Checkin", {"attendance": doc.name}, cache=True)
        if checkins and checkins > 0:
            if is_holiday.get("is_weekly_off"):
                status = "POW"
            else:
                status = "POH"
        else:
            if is_holiday.get("is_weekly_off"):
                status = "WO"
            else:
                status = "HO"

    frappe.db.set_value("Attendance", doc.name, "custom_attendance_tag", status)

    if status == "Half Day" and doc.leave_application:
        half_day_date = frappe.db.get_value("Leave Application", doc.leave_application, "half_day_date")
        if half_day_date and getdate(half_day_date) == getdate(doc.attendance_date):
            half_type = frappe.db.get_value("Leave Application", doc.leave_application, "custom_half_type")
            frappe.db.set_value("Attendance", doc.name, "custom_half_type", half_type)


def allocate_incentive(doc):
    def _create_additional_salary(employee: str, amount):
        new_additional_salary = frappe.get_doc(
            dict(
                doctype="Additional Salary",
                employee=employee,
                payroll_date=get_last_day(getdate()),
                salary_component="Incentives",
                leave_type="Compensatory Off",
                amount=amount,
            )
        )
        new_additional_salary.insert(ignore_permissions=True)
        new_additional_salary.submit()

    def _create_incentive_log(employee: str, amount, from_date, to_date, work_date, status):
        incentive_log = frappe.get_doc(
            dict(
                doctype="Incentive Log",
                employee=employee,
                from_date=from_date,
                to_date=to_date,
                leave_type="Compensatory Off",
                incentive=amount,
                work_date=work_date,
                status=status,
            )
        )
        incentive_log.insert(ignore_permissions=True)
        incentive_log.submit()

    def round_incentive(amount):
        return (amount // 25) * 25

    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    date_of_joining = employee.date_of_joining

    # Do we even need this check? Attendance cannot be created before date of joining
    if date_of_joining and getdate(doc.attendance_date) < date_of_joining:
        return

    grade = employee.grade
    branch = employee.branch
    grade_doc = frappe.get_cached_doc("Employee Grade", grade, for_update=False)

    if grade_doc.custom_present_on_holiday != "Incentive" and grade_doc.custom_extra_work_hour != "Incentive":
        return

    hours = doc.working_hours
    checkins = frappe.db.exists("Employee Checkin", {"attendance": doc.name}, cache=True)
    if not hours or hours == 0:
        return
    status = ""
    holiday = is_holiday_for_employee(doc.employee, doc.attendance_date)
    if holiday and holiday.get("is_holiday") and not checkins:
        return  # It is holiday and employee did not worked.

    if holiday and holiday.get("is_holiday") and holiday.get("is_weekly_off"):
        status = "POW"
    else:
        status = "POH"

    shift = doc.shift
    shift = frappe.get_cached_doc("Shift Type", shift) if shift else None
    if not shift:
        return

    shift_duration = convert_time_to_hours(shift.custom_shift_time)

    if hours <= shift_duration:
        return

    c_matrix = frappe.db.exists(
        "Compensation Matrix", {"shift_duration": timedelta(hours=shift_duration), "branch": branch}, cache=True
    )
    if not c_matrix:
        return
    c_matrix = frappe.get_cached_doc("Compensation Matrix", c_matrix)

    if holiday and holiday.get("is_holiday") and grade_doc.custom_present_on_holiday == "Incentive":
        diff = hours

    if not holiday and grade_doc.custom_extra_work_hour == "Incentive":
        diff = hours - shift_duration
        status = "EW"
    worked_hrs_in_delta = timedelta(hours=diff)
    matched_c_matrix = next((m for m in c_matrix.items if m.from_hrs < worked_hrs_in_delta <= m.to_hrs), None)
    if not matched_c_matrix:
        return
    credit = matched_c_matrix.c_off_credit
    if not credit:
        return

    salary_structure_name = frappe.db.get_value(
        "Salary Structure Assignment",
        {"employee": employee.name},
        fieldname="salary_structure",
        cache=True,
        order_by="creation desc",
    )
    earning = (
        frappe.db.get_value(
            "Salary Structure",
            salary_structure_name,
            fieldname="total_earning",
            cache=True,
        )
        or 0
    )
    month_start = get_first_day(getdate())
    month_end = get_last_day(getdate())
    additional_incentive = (earning / (date_diff(month_end, month_start) + 1)) * credit

    existing_incentive = frappe.db.get_value(
        "Additional Salary",
        {
            "employee": employee.name,
            "salary_component": "Incentive",
            "payroll_date": ("between", (month_start, month_end)),
            "docstatus": 1,
        },
        fieldname="name",
    )

    if existing_incentive:
        additional_salary = frappe.get_doc("Additional Salary", existing_incentive)
        additional_incentive += additional_salary.amount
        additional_salary.cancel()
        additional_salary.delete()

    additional_incentive = round_incentive(additional_incentive)

    _create_additional_salary(employee.name, additional_incentive)
    _create_incentive_log(employee.name, additional_incentive, month_start, month_end, doc.attendance_date, status)


def allocate_c_off(doc):
    employee = frappe.get_cached_doc("Employee", doc.employee, for_update=False)
    grade = employee.grade
    branch = employee.branch
    grade_doc = frappe.get_cached_doc("Employee Grade", grade, for_update=False)

    if grade_doc.custom_present_on_holiday != "Comp Off" and grade_doc.custom_extra_work_hour != "Comp Off":
        return

    hours = doc.working_hours
    checkins = frappe.db.exists("Employee Checkin", {"attendance": doc.name}, cache=True)
    if not hours or hours == 0:
        return

    status = ""
    holiday = is_holiday_for_employee(doc.employee, doc.attendance_date)
    if holiday and holiday.get("is_holiday") and not checkins:
        return  # It is holiday and employee did not worked.

    if holiday and holiday.get("is_holiday") and holiday.get("is_weekly_off"):
        status = "POW"
    else:
        status = "POH"

    shift = doc.shift
    shift = frappe.get_cached_doc("Shift Type", shift) if shift else None
    if not shift:
        return

    shift_duration = convert_time_to_hours(shift.custom_shift_time)
    if hours <= shift_duration:
        return
    c_matrix = frappe.db.exists(
        "Compensation Matrix", {"shift_duration": timedelta(hours=shift_duration), "branch": branch}, cache=True
    )
    if not c_matrix:
        return
    c_matrix = frappe.get_cached_doc("Compensation Matrix", c_matrix)

    if holiday and holiday.get("is_holiday") and grade_doc.custom_present_on_holiday == "Comp Off":
        diff = hours

    if not holiday and grade_doc.custom_extra_work_hour == "Comp Off":
        diff = hours - shift_duration
        status = "EW"
    worked_hrs_in_delta = timedelta(hours=diff)

    matched_c_matrix = next((m for m in c_matrix.items if m.from_hrs < worked_hrs_in_delta <= m.to_hrs), None)
    if not matched_c_matrix:
        return

    credit = matched_c_matrix.c_off_credit
    if not credit:
        return

    comp_off = frappe.get_doc(
        {
            "doctype": "Compensatory Leave Request",
            "employee": employee.name,
            "work_from_date": getdate(doc.attendance_date),
            "work_end_date": getdate(doc.attendance_date),
            "credit": credit,
            "leave_type": "Compensatory Off",
            "status": f"{status}:{diff}",
            "expiry": add_days(getdate(doc.attendance_date), grade_doc.custom_comp_off_validity),
            "reason": status,
        }
    )
    comp_off.insert(ignore_permissions=True, ignore_if_duplicate=True)
    try:
        comp_off.submit()
    except Exception:
        if comp_off.docstatus.is_submitted():
            comp_off.cancel()
        frappe.log_error(
            frappe.get_traceback(), f"Comp-Off Allocation Failed for {doc.employee} on {doc.attendance_date}"
        )
