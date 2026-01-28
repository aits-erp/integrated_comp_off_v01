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
        reason: DF.Literal["", "Personal", "Work"]
        reason_detail: DF.SmallText
        status: DF.Literal["Draft", "Pending", "Rejected", "Approved"]

    # end: auto-generated types
    def validate(self):
        self.validate_single_gate_pass_per_day()

    def before_insert(self):
        self.validate_date()
        self.validate_checkin()
        self.validate_branch()

    def validate_single_gate_pass_per_day(self):
        if not self.employee or not self.date:
            return

        existing = frappe.get_all(
            "Gate Pass",
            filters=[
                ["employee", "=", self.employee],
                ["date", "=", self.date],
                ["docstatus", "in", [0, 1]],
                ["name", "!=", self.name or ""],
            ],
            pluck="name",
            limit=1,
        )

        if existing:
            frappe.throw(
                frappe._("You have already applied for a Gate Pass for this date."),
                title=frappe._("Duplicate Gate Pass"),
            )

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
