import frappe
from frappe.utils import flt, getdate
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip


class SalarySlipOverride(SalarySlip):
    def validate(self):
        super().validate()
        self.set_total_deduction_with_loan()

    def set_total_deduction_with_loan(self):
        total_loan_repayment = flt(self.get("total_loan_repayment"))
        if not total_loan_repayment:
            self.custom_total_deduction_with_loan = flt(self.total_deduction)
            return
        self.custom_total_deduction_with_loan = flt(self.total_deduction) + total_loan_repayment

    def calculate_lwp_ppl_and_absent_days_based_on_attendance(
        self,
        holidays,
        daily_wages_fraction_for_half_day,
        consider_marked_attendance_on_holidays,
    ):
        lwp, absent = super().calculate_lwp_ppl_and_absent_days_based_on_attendance(
            holidays=holidays,
            daily_wages_fraction_for_half_day=daily_wages_fraction_for_half_day,
            consider_marked_attendance_on_holidays=consider_marked_attendance_on_holidays,
        )

        leave_type_map = self.get_leave_type_map()
        attendance_details = self.get_employee_attendance(
            start_date=self.start_date, end_date=self.actual_end_date
        )

        extra_absent = 0.0
        absent_equivalent_for_half_day = 1 - daily_wages_fraction_for_half_day

        for attendance in attendance_details:
            if attendance.status != "Half Day" or not attendance.leave_type:
                continue

            # Leave types already counted under LWP/PPL in base logic should not be counted again.
            if attendance.leave_type in leave_type_map:
                continue

            if (
                not consider_marked_attendance_on_holidays
                and getdate(attendance.attendance_date) in holidays
            ):
                continue

            extra_absent += absent_equivalent_for_half_day

        return lwp, absent + extra_absent
