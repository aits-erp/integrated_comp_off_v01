# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate

from real_group.tasks.process_employee_checkin import get_first_checkin_for_the_day


class GatePass(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        date: DF.Date
        employee: DF.Link
        employee_name: DF.Data | None
        name: DF.Int | None
        reason: DF.SmallText
        status: DF.Literal["Draft", "Pending", "Rejected", "Approved"]

    # end: auto-generated types
    def before_insert(self):
        self.validate_date()
        self.validate_checkin()

    def validate_date(self):
        if getdate(self.date) < getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for {}.").format(self.date))

    def validate_checkin(self):
        has_checkin = get_first_checkin_for_the_day(self.employee, get_datetime())
        if not has_checkin:
            frappe.throw(frappe._("Employee  has not checked in today. Cannot create Gate Pass."))


def expire_gate_passes():
    gate_passes = frappe.get_all(
        "Gate Pass",
        filters={"docstatus": 0, "date": ("<", getdate())},
        pluck="name",
    )
    for gate_pass in gate_passes:
        doc = frappe.get_doc("Gate Pass", gate_pass)
        doc.status = "Rejected"
        doc.submit()
