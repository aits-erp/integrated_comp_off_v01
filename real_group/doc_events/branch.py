import frappe


def on_update(doc, method):
    if doc.has_value_changed("custom_holiday_list"):
        employees = frappe.get_all("Employee", filters={"branch": doc.name, "status": "Active"}, pluck="name")
        for e in employees:
            frappe.db.set_value("Employee", e, "holiday_list", doc.custom_holiday_list)
