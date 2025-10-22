import datetime

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_url_to_list
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import CompensatoryLeaveRequest
from hrms.hr.utils import create_additional_leave_ledger_entry, get_leave_period


class CompensatoryLeaveRequestOverride(CompensatoryLeaveRequest):
    def validate_holidays(self):
        pass

    def validate_attendance(self):
        pass

    def on_submit(self):
        company = frappe.db.get_value("Employee", self.employee, "company")

        date_difference = self.credit

        comp_leave_valid_from = add_days(self.work_end_date, 1)
        leave_period = get_leave_period(comp_leave_valid_from, comp_leave_valid_from, company)
        if leave_period:
            leave_allocation = self.get_existing_allocation(comp_leave_valid_from)
            if leave_allocation:
                leave_allocation.new_leaves_allocated += date_difference
                leave_allocation.validate()
                leave_allocation.db_set("new_leaves_allocated", leave_allocation.total_leaves_allocated)
                leave_allocation.db_set("total_leaves_allocated", leave_allocation.total_leaves_allocated)

                # generate additional ledger entry for the new compensatory leaves off
                create_additional_leave_ledger_entry(leave_allocation, date_difference, comp_leave_valid_from)

            else:
                leave_allocation = self.create_leave_allocation(leave_period, date_difference)
            self.db_set("leave_allocation", leave_allocation.name)
        else:
            comp_leave_valid_from = frappe.bold(frappe.utils.format_date(comp_leave_valid_from))
            msg = _("This compensatory leave will be applicable from {0}.").format(comp_leave_valid_from)
            msg += " " + _(
                "Currently, there is no {0} leave period for this date to create/update leave allocation."
            ).format(frappe.bold(_("active")))
            msg += "<br><br>" + _("Please create a new {0} for the date {1} first.").format(
                f"""<a href='{get_url_to_list("Leave Period")}'>Leave Period</a>""",
                comp_leave_valid_from,
            )
            frappe.throw(msg, title=_("No Leave Period Found"))

    def on_cancel(self):
        if self.leave_allocation:
            date_difference = self.credit

            leave_allocation = frappe.get_doc("Leave Allocation", self.leave_allocation)
            if leave_allocation:
                leave_allocation.new_leaves_allocated -= date_difference
                if leave_allocation.new_leaves_allocated - date_difference <= 0:
                    leave_allocation.new_leaves_allocated = 0
                leave_allocation.validate()
                leave_allocation.db_set("new_leaves_allocated", leave_allocation.total_leaves_allocated)
                leave_allocation.db_set("total_leaves_allocated", leave_allocation.total_leaves_allocated)

                # create reverse entry on cancelation
                create_additional_leave_ledger_entry(
                    leave_allocation, date_difference * -1, add_days(self.work_end_date, 1)
                )

    def create_leave_allocation(self, leave_period, date_difference):
        is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
        allocation = frappe.get_doc(
            dict(
                doctype="Leave Allocation",
                employee=self.employee,
                employee_name=self.employee_name,
                leave_type=self.leave_type,
                from_date=add_days(self.work_end_date, 1),
                to_date=self.expiry,
                carry_forward=cint(is_carry_forward),
                new_leaves_allocated=date_difference,
                total_leaves_allocated=date_difference,
                description=self.reason,
            )
        )
        allocation.insert(ignore_permissions=True)
        allocation.submit()
        return allocation

    # Taken from latest frappe hrms codebase
    def get_existing_allocation(self, comp_leave_valid_from: datetime.date) -> dict | None:
        leave_allocation = frappe.db.get_all(
            "Leave Allocation",
            filters={
                "employee": self.employee,
                "leave_type": self.leave_type,
                "from_date": ("<=", comp_leave_valid_from),
                "to_date": (">=", comp_leave_valid_from),
                "docstatus": 1,
            },
            limit=1,
        )

        if leave_allocation:
            return frappe.get_doc("Leave Allocation", leave_allocation[0].name)
        else:
            return False
