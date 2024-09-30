import frappe
from frappe.core.doctype.user.user import User
from erpnext.setup.doctype.employee.employee import Employee
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin, validate_active_employee
from hrms.hr.doctype.leave_application.leave_application import get_approved_leaves_for_period, get_leave_balance_on
from frappe.utils import add_days, date_diff, flt, formatdate, get_link_to_form, getdate
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import CompensatoryLeaveRequest
from hrms.hr.utils import (
	create_additional_leave_ledger_entry,
	get_holiday_dates_for_employee,
	get_leave_period,
	validate_active_employee,
	validate_dates,
	validate_overlap,
)

class CustomUser(User):

	def autoname(self):
		"""set name as Email Address"""
		if self.get("is_admin") or self.get("is_guest"):
			self.name = self.first_name
		else:
			# self.email = self.email.strip().lower()
			self.name = self.username
	def validate_email_type(self, email):
		pass


class CustomEmployee(Employee):

	def autoname(self):

		count = frappe.db.count("Employee", filters={"company": self.company})
		start_from = frappe.db.get_value("Company", self.company, "custom_employee_code_starting_from")
		ending_at = frappe.db.get_value("Company", self.company, "custom_employee_code_ending_at")

		if (start_from + count + 1) > ending_at:
			frappe.throw("Cannot create new employee: Please update the naming series to continue or contact admin")

		self.name = str(start_from + count + 1)

class CustomEmployeeCheckin(EmployeeCheckin):
	def validate(self):
		validate_active_employee(self.employee)
		self.validate_duplicate_log()
		# self.fetch_shift()


class CustomCompensatoryLeaveRequest(CompensatoryLeaveRequest):
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
			leave_allocation = self.get_existing_allocation_for_period(leave_period)
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
			comp_leave_valid_from = frappe.bold(format_date(comp_leave_valid_from))
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
		if self.custom_is_expired == 1:
			frappe.throw("This document is expired. You cannot cancel this document")
		if self.leave_allocation:
			# no. of leaves
			date_difference = self.credit

			leave_balance = get_leave_balance_on(
					self.employee,
					self.leave_type,
					self.work_from_date,
					self.work_end_date,
					consider_all_leaves_in_the_allocation_period=True,
					for_consumption=True,
				)
			
			actual_balance = float(leave_balance.get("leave_balance")) + date_difference
			if date_difference > actual_balance:
				frappe.throw("The leaves are already utilized for this leave allocation. You cannot cancel this entry")
			if date_difference <= actual_balance:
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
					