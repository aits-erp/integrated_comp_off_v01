# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate

from real_group.helper.attendance_helper import get_weekly_off


class WeeklyHolidayUpdateRequest(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        employee: DF.Link
        name: DF.Int | None
        valid_from: DF.Date
        weekly_off: DF.Link

    # end: auto-generated types
    def on_submit(self):
        if (
            (hasattr(self, "flags") and self.flags.ignore_update_employee)
            or getdate(self.valid_from) < getdate()
            or getdate() < getdate(self.valid_from)
        ):
            return
        self.update_weekly_off_in_employee()

    def update_weekly_off_in_employee(self):
        employee = frappe.get_doc("Employee", self.employee)
        employee.custom_weekly_holiday_list = self.weekly_off
        employee.save()

    def validate(self):
        self.validate_date()
        self.validate_back_dated()
        get_weekly_off.clear_cache()

    def validate_date(self):
        date = getdate(self.valid_from)
        exists = frappe.db.exists(
            "Weekly Holiday Update Request",
            {
                "employee": self.employee,
                "valid_from": ("=", date),
                "name": ("!=", self.name),
                "docstatus": 1,
            },
        )
        if exists:
            frappe.throw(
                frappe._("Another {0} exists for this employee with same valid from date.").format(
                    get_link_to_form("Weekly Holiday Update Request", exists, "Weekly Holiday Update Request")
                )
            )

    def validate_back_dated(self):
        date = getdate(self.valid_from)
        data = frappe.db.get_value(
            "Weekly Holiday Update Request",
            {
                "employee": self.employee,
                "docstatus": 1,
            },
            ["name", "valid_from"],
        )
        if not data:
            return
        name, back_date = data
        if back_date and date < getdate(back_date):
            frappe.throw(
                frappe._("Valid From date cannot be before {0} for this employee. As there is existing {1}.").format(
                    back_date, get_link_to_form("Weekly Holiday Update Request", name, "request")
                )
            )
