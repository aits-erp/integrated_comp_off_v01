# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, get_first_day, get_last_day


class ShortLeave(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        employee: DF.Link
        for_date: DF.Date
        punch_time: DF.Datetime
        shift: DF.Link | None
        shift_start_time: DF.Datetime

    # end: auto-generated types
    def validate(self):
        self.validate_short_leave_request()

    def validate_short_leave_request(self):
        grade = frappe.get_cached_value("Employee", self.employee, "grade")
        grade = frappe.get_cached_doc("Employee Grade", grade)

        from_date = get_first_day(self.for_date)
        to_date = get_last_day(self.for_date)

        if not (grade.custom_hours_per_leave):
            frappe.throw(frappe._("Not Eligible for short leave, kindly avail Short Leave on Employee Grade"))

        diff = get_datetime(self.punch_time) - get_datetime(self.shift_start_time)
        if grade.custom_hours_per_leave:
            if diff > grade.custom_hours_per_leave and self.reason == grade.custom_short_leave_type:
                frappe.throw(frappe._("Short Leave is not allowed beyond Short Leave Time Allowed "))

        if (
            frappe.db.count(
                "Short Leave",
                {
                    "employee": self.employee,
                    "for_date": ["between", [from_date, to_date]],
                    "docstatus": ["!=", 2],
                    "name": ["!=", self.name],
                },
            )
            > grade.custom_number_of_leaves
        ):
            frappe.throw(frappe._("Short Leave Limit Exceeded, Contact your HR Manager"))
