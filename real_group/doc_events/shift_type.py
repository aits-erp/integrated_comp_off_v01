from frappe.utils import get_timedelta


def validate(doc, method=None):
    doc.custom_shift_time = abs(get_timedelta(doc.start_time) - get_timedelta(doc.end_time))
