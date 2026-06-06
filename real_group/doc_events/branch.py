import frappe


def validate(doc, method):
    value = doc.get("custom_allowed_mis_punch_days")
    doc.custom_allowed_mis_punch_days = get_two_digit_value(value)


def on_update(doc, method):
    if doc.has_value_changed("custom_holiday_list"):
        employees = frappe.get_all("Employee", filters={"branch": doc.name, "status": "Active"}, pluck="name")
        for e in employees:
            frappe.db.set_value("Employee", e, "holiday_list", doc.custom_holiday_list)


def get_two_digit_value(value):
    if value in (None, ""):
        return value

    digits = "".join(char for char in str(value) if char.isdigit())
    if not digits:
        return None

    return int(digits[:2])
