# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReprocessAttendanceBulk(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        branch: DF.Link | None
        company: DF.Link
        department: DF.Link | None
        division: DF.Link | None
        employee: DF.Link | None
        month: DF.Literal["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        year: DF.Literal["", "2023", "2024"]
    # end: auto-generated types

    def on_submit(self):
        # self.create_reprocess_attendance()
        data = self.get_reprocess_attendance()
        for d in data:
            reprocess_attendance = frappe.get_doc("Reprocess Attendance", d)
            reprocess_attendance.submit()

    def get_reprocess_attendance(self):
        return frappe.get_all(
            "Reprocess Attendance",
            filters={"reprocess_attendance_bulk": self.name},
            pluck="name",
        )

    def after_insert(self):
        self.create_reprocess_attendance()

    def create_reprocess_attendance(self):
        employees = self.get_employees()
        for emp in employees:
            reprocess_attendance = frappe.get_doc(
                dict(
                    doctype="Reprocess Attendance",
                    company=self.company,
                    branch=self.branch,
                    division=self.division,
                    department=self.department,
                    month=self.month,
                    year=self.year,
                    reprocess_attendance_bulk=self.name,
                    employee=emp,
                )
            )
            reprocess_attendance.save()

    def get_employees(self):
        filters = {"status": "Active"}
        if self.company:
            filters["company"] = self.company
        if self.branch:
            filters["branch"] = self.branch
        if self.division:
            filters["custom_division"] = self.division
        if self.department:
            filters["department"] = self.department
        if self.employee:
            filters["name"] = self.employee
        return frappe.get_all("Employee", filters=filters, pluck="name")
