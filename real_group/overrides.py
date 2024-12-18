import frappe
from frappe import _
from frappe.core.doctype.user.user import User
from erpnext.setup.doctype.employee.employee import Employee
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin, validate_active_employee
from hrms.hr.doctype.leave_application.leave_application import get_approved_leaves_for_period, get_leave_balance_on
from frappe.utils import add_days, date_diff, flt, formatdate, get_link_to_form, getdate, cint, get_url, format_date, get_url_to_list
from hrms.hr.doctype.compensatory_leave_request.compensatory_leave_request import CompensatoryLeaveRequest
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
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
					


@frappe.whitelist(allow_guest=True)
def send_login_link(email: str):

	if not frappe.get_system_settings("login_with_email_link"):
		return

	expiry = frappe.get_system_settings("login_with_email_link_expiry") or 10
	link = _generate_temporary_login_link(email, expiry)

	app_name = (
		frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name") or _("Frappe")
	)

	subject = _("Login To {0}").format(app_name)

	email = frappe.db.get_value("User", email, "email")

	frappe.sendmail(
		subject=subject,
		recipients=email,
		template="login_with_email_link",
		args={"link": link, "minutes": expiry, "app_name": app_name},
		now=True,
	)

def _generate_temporary_login_link(email: str, expiry: int):
	assert isinstance(email, str)

	if not frappe.db.exists("User", email):
		frappe.throw(_("User with email address {0} does not exist").format(email), frappe.DoesNotExistError)
	key = frappe.generate_hash()
	frappe.cache.set_value(f"one_time_login_key:{key}", email, expires_in_sec=expiry * 60)

	return get_url(f"/api/method/frappe.www.login.login_via_key?key={key}")

# Keep it for few months unless we need to override.

# class CustomLeaveApplication(LeaveApplication):
# 	def create_or_update_attendance(self, attendance_name, date):
		
# 		if self.half_day == 1:
# 			if self.from_date == self.to_date:
# 				half_day_date = self.from_date
# 				from_time = str(half_day_date) + " " + "00:00:00"
# 				to_time = str(half_day_date) + " " + "23:59:59"
# 				query = frappe.db.sql(f"""
# 					SELECT
# 						ec.employee AS employee,
# 						MIN(CASE WHEN ec.log_type = 'IN' THEN TIME(ec.time) END) AS in_time,
# 						MAX(CASE WHEN ec.log_type = 'OUT' THEN TIME(ec.time) END) AS out_time,
# 						ec.shift
# 					FROM 
# 						`tabEmployee Checkin` ec
# 					WHERE
# 						ec.time BETWEEN '{from_time}' AND '{to_time}'
# 						AND ec.employee = '{self.employee}'
# 					GROUP BY
# 						ec.employee, ec.shift
# 				""", as_dict=True)
# 				if len(query) > 0:	
# 					for i in query:	
# 						if (i.get("in_time") is not None and i.get("in_time") != "") and (i.get("out_time") is not None and i.get("out_time") != ""):
# 							shift = frappe.get_doc("Shift Type", query[0].get("shift"))
# 							if query[0].get("out_time") - query[0].get("in_time") > shift.custom_present_threshold:
# 								status = "Present"
# 								if attendance_name:
# 									# update existing attendance, change absent to on leave
# 									doc = frappe.get_doc("Attendance", attendance_name)
# 									doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
# 								else:
# 									# make new attendance and submit it
# 									doc = frappe.new_doc("Attendance")
# 									doc.employee = self.employee
# 									doc.employee_name = self.employee_name
# 									doc.attendance_date = date
# 									doc.company = self.company
# 									doc.leave_type = self.leave_type
# 									doc.leave_application = self.name
# 									doc.status = status
# 									doc.flags.ignore_validate = True
# 									doc.insert(ignore_permissions=True)
# 									doc.submit()
# 			elif (self.half_day_date is not None or self.half_day_date != ""):
# 				half_day_date = self.half_day_date
# 				from_time = str(half_day_date) + " " + "00:00:00"
# 				to_time = str(half_day_date) + " " + "23:59:59"
# 				query = frappe.db.sql(f"""
# 					SELECT
# 						ec.employee AS employee,
# 						MIN(CASE WHEN ec.log_type = 'IN' THEN TIME(ec.time) END) AS in_time,
# 						MAX(CASE WHEN ec.log_type = 'OUT' THEN TIME(ec.time) END) AS out_time,
# 						ec.shift
# 					FROM 
# 						`tabEmployee Checkin` ec
# 					WHERE
# 						ec.time BETWEEN '{from_time}' AND '{to_time}'
# 						AND ec.employee = '{self.employee}'
# 					GROUP BY
# 						ec.employee, ec.shift
# 				""", as_dict=True)

# 				if len(query) > 0:	
# 					for i in query:	
# 						if (i.get("in_time") is not None and i.get("in_time") != "") and (i.get("out_time") is not None and i.get("out_time") != ""):
# 							shift = frappe.get_doc("Shift Type", query[0].get("shift"))
# 							if query[0].get("out_time") - query[0].get("in_time") > shift.custom_half_day_threshold:
# 								status = "Present"
# 								if attendance_name:
# 									# update existing attendance, change absent to on leave
# 									doc = frappe.get_doc("Attendance", attendance_name)
# 									doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
# 								else:
# 									# make new attendance and submit it
# 									doc = frappe.new_doc("Attendance")
# 									doc.employee = self.employee
# 									doc.employee_name = self.employee_name
# 									doc.attendance_date = date
# 									doc.company = self.company
# 									doc.leave_type = self.leave_type
# 									doc.leave_application = self.name
# 									doc.status = status
# 									doc.flags.ignore_validate = True
# 									doc.insert(ignore_permissions=True)
# 									doc.submit()
# 			else:
# 				status = (
# 					"Half Day" if self.half_day_date and getdate(date) == getdate(self.half_day_date) else "On Leave"
# 				)
# 				if attendance_name:
# 					# update existing attendance, change absent to on leave
# 					doc = frappe.get_doc("Attendance", attendance_name)
# 					doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
# 				else:
# 					# make new attendance and submit it
# 					doc = frappe.new_doc("Attendance")
# 					doc.employee = self.employee
# 					doc.employee_name = self.employee_name
# 					doc.attendance_date = date
# 					doc.company = self.company
# 					doc.leave_type = self.leave_type
# 					doc.leave_application = self.name
# 					doc.status = status
# 					doc.flags.ignore_validate = True
# 					doc.insert(ignore_permissions=True)
# 					doc.submit()
		
# 		else:
# 			status = (
# 				"Half Day" if self.half_day_date and getdate(date) == getdate(self.half_day_date) else "On Leave"
# 			)
# 			if attendance_name:
# 				# update existing attendance, change absent to on leave
# 				doc = frappe.get_doc("Attendance", attendance_name)
# 				doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
# 			else:
# 				# make new attendance and submit it
# 				doc = frappe.new_doc("Attendance")
# 				doc.employee = self.employee
# 				doc.employee_name = self.employee_name
# 				doc.attendance_date = date
# 				doc.company = self.company
# 				doc.leave_type = self.leave_type
# 				doc.leave_application = self.name
# 				doc.status = status
# 				doc.flags.ignore_validate = True
# 				doc.insert(ignore_permissions=True)
# 				doc.submit()


