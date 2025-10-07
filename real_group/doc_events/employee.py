import frappe


def autoname(doc, method):
    count = frappe.db.count("Employee", filters={"company": doc.company})
    start_from = frappe.db.get_value("Company", doc.company, "custom_employee_code_starting_from")
    ending_at = frappe.db.get_value("Company", doc.company, "custom_employee_code_ending_at")

    if (start_from + count + 1) > ending_at:
        frappe.throw("Cannot create new employee: Please update the naming series to continue or contact admin")

    doc.name = str(start_from + count + 1)
