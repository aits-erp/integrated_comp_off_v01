import frappe


@frappe.whitelist()
def get_leave_on_dates(employee, from_date, to_date):
    leave_on_dates = frappe.db.get_all(
        "Leave Application",
        filters={
            "employee": employee,
            "docstatus": ["!=", 2],
            "from_date": ["<=", to_date],
            "to_date": [">=", from_date],
        },
        fields=["name", "from_date", "to_date", "half_day", "half_day_date", "status"],
    )
    return leave_on_dates
