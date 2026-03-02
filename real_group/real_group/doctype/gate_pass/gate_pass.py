# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate


class GatePass(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        checkout_time: DF.Datetime | None
        date: DF.Date
        employee: DF.Link
        employee_name: DF.Data | None
        name: DF.Int | None
        reason: DF.Literal["", "Personal", "Official"]
        reason_detail: DF.SmallText
        status: DF.Literal["Draft", "Pending", "Rejected", "Approved"]

    # end: auto-generated types
    def validate(self):
        self.validate_total_gate_pass_per_day()
        self.validate_checkout_before_approval()

    def before_insert(self):
        self.validate_date()
        self.validate_checkin()
        self.validate_branch()

    def validate_total_gate_pass_per_day(self):
        if not self.employee or not self.date:
            return

        in_log_count = get_in_log_count(self.employee, self.date)
        if in_log_count <= 0:
            frappe.throw(frappe._("Employee has not checked in today. Cannot create Gate Pass."))

        existing_gate_passes = frappe.get_all(
            "Gate Pass",
            filters=[
                ["employee", "=", self.employee],
                ["date", "=", self.date],
                ["docstatus", "in", [0, 1]],
                ["name", "!=", self.name or ""],
            ],
            pluck="name",
        )

        if len(existing_gate_passes) >= in_log_count:
            frappe.throw(
                frappe._("You can create at most {0} Gate Pass(es) for this date based on your check-ins.").format(
                    in_log_count
                ),
                title=frappe._("Gate Pass Limit Reached"),
            )

    def validate_date(self):
        if getdate(self.date) < getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for past dates"))
        if getdate(self.date) > getdate():
            frappe.throw(frappe._("Gate Pass date cannot be created for future dates"))

    def validate_checkin(self):
        in_log_count = get_in_log_count(self.employee, self.date)
        if in_log_count <= 0:
            frappe.throw(frappe._("Employee has not checked in today. Cannot create Gate Pass."))

    def validate_branch(self):
        branch = frappe.db.get_value("Employee", self.employee, "branch")
        if not branch:
            return
        skip_gate_pass = frappe.db.get_value("Branch", branch, "custom_skip_gate_pass")
        if skip_gate_pass == 1:
            frappe.throw(frappe._("Branch doesn't allow gate pass."))

    def validate_checkout_before_approval(self):
        is_approved_state = False
        if self.meta.has_field("workflow_state"):
            is_approved_state = self.workflow_state == "Approved"
        else:
            is_approved_state = self.status == "Approved"

        if not is_approved_state or not self.employee or not self.date:
            return

        latest_checkout = get_latest_checkout_time(self.employee, str(self.date))
        if not latest_checkout:
            frappe.throw(
                frappe._("Employee has not checked out yet. Gate Pass cannot be approved before checkout.")
            )

        self.checkout_time = latest_checkout


def get_in_log_count(employee: str, date: str) -> int:
    if not employee or not date:
        return 0

    start_time = get_datetime(date)
    end_time = get_datetime(add_days(getdate(date), 1))
    in_logs = frappe.get_all(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee],
            ["log_type", "=", "IN"],
            ["time", ">=", start_time],
            ["time", "<", end_time],
        ],
        pluck="name",
    )
    return len(in_logs)


def expire_gate_passes():
    gate_passes = frappe.get_all(
        "Gate Pass",
        filters={"docstatus": 0, "date": ("<", getdate())},
        pluck="name",
    )
    for gate_pass in gate_passes:
        doc = frappe.get_doc("Gate Pass", gate_pass)
        doc.status = "Rejected"
        if doc.meta.has_field("workflow_state") and doc.workflow_state == "Gate Pass":
            doc.workflow_state = "Rejected at Gate"
        doc.submit()


@frappe.whitelist()
def get_latest_checkout_time(employee: str, date: str):
    if not employee or not date:
        return None

    gate_pass_date = getdate(date)
    start_time = get_datetime(gate_pass_date)
    end_time = get_datetime(add_days(gate_pass_date, 1))

    latest_out = frappe.get_list(
        "Employee Checkin",
        filters=[
            ["employee", "=", employee],
            ["log_type", "=", "OUT"],
            ["time", ">=", start_time],
            ["time", "<", end_time],
        ],
        pluck="time",
        order_by="time desc",
        limit=1,
    )

    return latest_out[0] if latest_out else None
