import frappe
from frappe.utils import cint, get_link_to_form

from real_group.real_group.integration import update_user


def autoname(doc, method):
    series = frappe.db.get_value(
        "Employee Series", {"company": doc.company, "is_active": 1}, ["start", "end"], as_dict=1
    )
    if not series:
        frappe.throw(
            f"No active Employee Series found for company {doc.company}. Please create and activate an Employee Series."
        )
    start_from = cint(series.start)
    ending_at = cint(series.end)

    last_emp = frappe.db.sql(
        """
        SELECT name FROM `tabEmployee`
        WHERE company = %s AND cast(name as unsigned) BETWEEN %s AND %s
        ORDER BY cast(name as unsigned) DESC
        LIMIT 1
        """,
        (doc.company, start_from, ending_at),
        as_dict=True,
    )
    if last_emp:
        last_number = cint(last_emp[0].name)
        next_number = last_number + 1
    else:
        next_number = start_from

    if next_number > ending_at:
        frappe.throw(
            f"Cannot create new employee: Series limit reached ({ending_at}). "
            "Please activate or create a new Employee Series."
        )

    doc.name = str(next_number)


def validate(doc, method=None):
    doc.attendance_device_id = doc.name
    doc.employee_number = doc.name
    validate_employee_data(doc)
    validate_aadhar(doc)


def after_insert(doc, method=None):
    weekly_off_update_doc = frappe.get_doc(
        {
            "doctype": "Weekly Holiday Update Request",
            "employee": doc.name,
            "valid_from": doc.date_of_joining,
            "weekly_off": doc.custom_weekly_holiday_list,
        }
    )
    weekly_off_update_doc.flags.ignore_update_employee = True
    weekly_off_update_doc.insert(ignore_permissions=True)
    weekly_off_update_doc.submit()


def on_update(doc, method=None):
    update_user_details(doc)
    update_leave_approvers_on_save(doc)


def update_user_details(doc):
    if not doc.has_value_changed("user_id"):
        return
    if not doc.user_id:
        return
    if str(doc.user_id).strip() != str(doc.name).strip():
        frappe.throw(frappe._("Employee ID and User ID must be same"))
    user = frappe.get_doc("User", doc.user_id)
    update_user(user, method=None)


def validate_aadhar(doc):
    if not doc.status == "Active" or doc.flags.ignore_aadhar_validation:
        return

    duplicate_aadhar = frappe.get_all(
        "Employee",
        filters={
            "custom_aadhar_number": doc.custom_aadhar_number,
            "status": "Active",
            "name": ["!=", doc.name],
        },
        fields=["name", "employee"],
    )

    if len(duplicate_aadhar) > 0:
        links = [get_link_to_form("Employee", d["name"]) for d in duplicate_aadhar]
        frappe.throw(
            f"Same Aadhar Number {doc.custom_aadhar_number} with the Active employees Records: " + ", ".join(links)
        )

    duplicate_pans = frappe.get_all(
        "Employee",
        filters={
            "pan_number": doc.pan_number,
            "status": "Active",
            "name": ["!=", doc.name],
        },
        fields=["name", "employee"],
    )

    if len(duplicate_pans) > 0:
        links = [get_link_to_form("Employee", d["name"]) for d in duplicate_pans]
        frappe.throw(f"Same PAN Number {doc.pan_number} with the Active employees Records: " + ", ".join(links))


def validate_employee_data(doc):
    if " " in doc.first_name:
        frappe.throw(frappe._("Spaces not allowed in First Name"))

    allocation_percentage = 0

    for n in doc.custom_nominee:
        allocation_percentage = allocation_percentage + n.allocation_percentage

    if allocation_percentage != 100:
        frappe.throw(frappe._("Incorrect Nominee Allocation Percentage, It shoud be 100% only."))

    if len(doc.custom_aadhar_number) != 12:
        frappe.throw(frappe._("Aadhar Number should have 12 digits"))

    if not doc.custom_aadhar_number.isdigit():
        frappe.throw(frappe._("Aadhar Number should have only digits"))


def update_leave_approvers_on_save(doc):
    if doc.has_value_changed("leave_approver"):
        new_approver = doc.leave_approver
        new_approver_name = frappe.db.get_value("User", new_approver, "full_name")
        employee_id = doc.name
        filters = {"employee": employee_id, "docstatus": 0}

        if doc.meta.has_field("workflow_state"):
            filters["workflow_state"] = "Draft"

        draft_applications = frappe.get_all("Leave Application", filters=filters, pluck="name")

        for app_name in draft_applications:
            try:
                frappe.db.set_value(
                    "Leave Application",
                    app_name,
                    {"leave_approver": new_approver, "leave_approver_name": new_approver_name},
                )

            except Exception as e:
                frappe.log_error(f"Failed to update Leave App {app_name}: {e}", "LEAVE_APPROVER_UPDATE_ERROR")

        frappe.db.commit()
