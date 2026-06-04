import frappe


def execute():
    if not frappe.db.exists("Custom Field", "Salary Structure Assignment-custom_basic_pay"):
        return

    frappe.db.sql(
        """
        UPDATE `tabSalary Structure Assignment` ssa
        SET ssa.custom_basic_pay = (
            SELECT sd.amount
            FROM `tabSalary Detail` sd
            WHERE
                sd.parent = ssa.salary_structure
                AND sd.parenttype = 'Salary Structure'
                AND sd.parentfield = 'earnings'
                AND sd.salary_component = 'Basic'
                AND sd.abbr = 'B'
            ORDER BY sd.idx ASC
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM `tabSalary Detail` sd
            WHERE
                sd.parent = ssa.salary_structure
                AND sd.parenttype = 'Salary Structure'
                AND sd.parentfield = 'earnings'
                AND sd.salary_component = 'Basic'
                AND sd.abbr = 'B'
        )
        """
    )

    frappe.clear_cache(doctype="Salary Structure Assignment")
