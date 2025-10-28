import frappe
from frappe import _
from frappe.utils import flt
from hrms.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation, get_carry_forwarded_leaves


class LeaveAllocationOverride(LeaveAllocation):
    @frappe.whitelist()
    def set_total_leaves_allocated(self):
        self.unused_leaves = flt(
            get_carry_forwarded_leaves(self.employee, self.leave_type, self.from_date, self.carry_forward),
            self.precision("unused_leaves"),
        )

        self.total_leaves_allocated = flt(
            flt(self.unused_leaves) + flt(self.new_leaves_allocated),
            self.precision("total_leaves_allocated"),
        )

        self.limit_carry_forward_based_on_max_allowed_leaves()

        if self.carry_forward:
            self.set_carry_forwarded_leaves_in_previous_allocation()

        leave_type = frappe.get_doc("Leave Type", self.leave_type)
        if (
            not self.total_leaves_allocated
            and not leave_type.is_earned_leave
            and not leave_type.is_compensatory
            and not leave_type.custom_calculate_based_on_working_days
        ):
            frappe.throw(_("Total leaves allocated is mandatory for Leave Type {0}").format(self.leave_type))
