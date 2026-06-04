import frappe


def execute():
    frappe.db.sql(
        """
        UPDATE `tabSalary Structure Assignment` ssa
        INNER JOIN `tabSalary Structure` ss
            ON ss.name = ssa.salary_structure
        SET ssa.base = ss.total_earning
        """
    )

    frappe.clear_cache(doctype="Salary Structure Assignment")
