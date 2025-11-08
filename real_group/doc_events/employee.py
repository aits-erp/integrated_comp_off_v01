import frappe
from frappe.utils import cint


def autoname(doc, method):
    series = frappe.db.get_value(
        "Employee Series", {"company": doc.company, "is_active": 1}, ["start", "end"], as_dict=1
    )
    if not series:
        frappe.throw(
            f"No active Employee Series found for company {doc.company}. "
            "Please create and activate an Employee Series."
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
