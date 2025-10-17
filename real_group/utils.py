from datetime import time, timedelta

from frappe.utils import get_time


def convert_time_to_seconds(time_str: str | time) -> float:
    if isinstance(time_str, str):
        time_str = get_time(time_str)

    return timedelta(hours=time_str.hour, minutes=time_str.minute, seconds=time_str.second).total_seconds()


def convert_time_to_minutes(time_str: str | time) -> float:
    seconds = convert_time_to_seconds(time_str)
    return seconds / 60


def convert_time_to_hours(time_str: str | time) -> float:
    seconds = convert_time_to_seconds(time_str)
    return seconds / 3600
