# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate

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
        reason: DF.Literal["", "Personal", "Work"]
        status: DF.Literal["Draft", "Pending", "Rejected", "Approved"]
    # end: auto-generated types
    def before_insert(self):
        self.validate_date()
        self.validate_checkin()
        self.validate_branch()

    def validate_date(self):
        if getdate(self.date) < getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for past dates"))
        if getdate(self.date) > getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for future dates"))

    def validate_checkin(self):
        has_checkin = get_checkin_exists(self.employee, getdate())
        if not has_checkin:
            frappe.throw(frappe._("Employee  has not checked in today. Cannot create Gate Pass."))
    def validate_branch(self):
        branch = frappe.db.get_value("Employee", self.employee, "branch")
        if not branch:
            return
        skip_gate_pass = frappe.db.get_value("Branch", branch, "custom_skip_gate_pass")
        if skip_gate_pass == 1:
            frappe.throw(frappe._("Branch doesn't allow gate pass."))

def get_checkin_exists(employee: str, date: str) -> bool:
    start_time = get_datetime(date)
    end_time = get_datetime(add_days(getdate(date), 1))
    checkin = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee],
            ["time", ">=", start_time],
            ["time", "<", end_time],
        ],
        pluck="name",
        limit=1,
    )
    return bool(checkin)
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
