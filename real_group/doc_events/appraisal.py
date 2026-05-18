import frappe


def before_insert(doc, method=None):
    if doc.company or not doc.appraisal_cycle:
        return

    doc.company = frappe.db.get_value("Appraisal Cycle", doc.appraisal_cycle, "company")
