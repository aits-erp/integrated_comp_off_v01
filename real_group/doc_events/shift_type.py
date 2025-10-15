from datetime import timedelta

from frappe.utils import get_timedelta


def validate(doc, method=None):
    start_delta = get_timedelta(doc.start_time)
    end_delta = get_timedelta(doc.end_time)
    if start_delta < end_delta:
        doc.custom_shift_time = timedelta(seconds=(end_delta - start_delta).total_seconds())
    else:
        doc.custom_shift_time = timedelta(seconds=(end_delta + timedelta(days=1) - start_delta).total_seconds())
