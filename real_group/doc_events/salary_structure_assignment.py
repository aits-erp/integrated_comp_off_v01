import frappe
from frappe.utils import flt


def before_save(doc, method=None):
    values = get_salary_structure_assignment_values(doc.salary_structure)
    doc.custom_basic_pay = values.get("basic_pay")
    doc.base = values.get("base")


@frappe.whitelist()
def get_salary_structure_assignment_values(salary_structure):
    return {
        "basic_pay": get_salary_structure_basic_pay(salary_structure),
        "base": get_salary_structure_total_earning(salary_structure),
    }


@frappe.whitelist()
def get_salary_structure_basic_pay(salary_structure):
    if not salary_structure:
        return 0

    basic_pay = frappe.db.get_value(
        "Salary Detail",
        filters={
            "parent": salary_structure,
            "parenttype": "Salary Structure",
            "parentfield": "earnings",
            "salary_component": "Basic",
            "abbr": "B",
        },
        fieldname="amount",
        order_by="idx asc",
    )

    return flt(basic_pay)


def get_salary_structure_total_earning(salary_structure):
    if not salary_structure:
        return 0

    return flt(frappe.db.get_value("Salary Structure", salary_structure, "total_earning"))
