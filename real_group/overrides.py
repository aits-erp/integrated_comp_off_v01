import frappe
from frappe.core.doctype.user.user import User
from erpnext.setup.doctype.employee.employee import Employee
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin, validate_active_employee
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