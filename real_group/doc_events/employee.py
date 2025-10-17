import frappe


def autoname(doc, method):
    series = frappe.db.get_value(
        "Employee Series", {"company": doc.company, "is_active": 1}, ["start", "end"], as_dict=1
    )
    count = frappe.db.count("Employee", filters={"company": doc.company})
    start_from = series.start
    ending_at = series.end

    name = start_from + count
    if name > ending_at:
        frappe.throw("Cannot create new employee: Please update the naming series to continue or contact admin")

    doc.name = str(name)
