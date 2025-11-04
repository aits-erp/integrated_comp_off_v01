# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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
        if hasattr(self, "flags") and self.flags.ignore_update_employee:
            return
        self.update_weekly_off_in_employee()

    def update_weekly_off_in_employee(self):
        employee = frappe.get_doc("Employee", self.employee)
        employee.custom_weekly_holiday_list = self.weekly_off
        employee.save()
