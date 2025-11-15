# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import remove as unassign
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
    def validate(self):
        self.validate_date()
        self.validate_checkin()

    def validate_date(self):
        if getdate(self.date) < getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for {}.").format(self.date))

    def validate_checkin(self):
        has_checkin = get_first_checkin_for_the_day(self.employee, get_datetime())
        if not has_checkin:
            frappe.throw(frappe._("Employee  has not checked in today. Cannot create Gate Pass."))

    def on_update(self):
        if hasattr(self, "workflow_state") and self.workflow_state == "Gate Pass":
            self.assign_to_gate_approver()

        if hasattr(self, "workflow_state") and self.workflow_state == "Approved":
            assigned_user = self.get_assigned_users()
            if assigned_user:
                unassign("Gate Pass", self.name, assign_to=assigned_user, ignore_permissions=True)

    def assign_to_gate_approver(self):
        approver = frappe.db.get_value("Employee", self.employee, "custom_gate_pass_approver")
        if not approver:
            frappe.throw(frappe._("No Gate Pass Approver assigned for Employee {0}.".format(self.employee)))
        args = {
            "assign_to": [approver],
            "doctype": "Gate Pass",
            "name": self.name,
            "description": "Gate Pass Approval Request",
        }
        assign(args, ignore_permissions=True)
