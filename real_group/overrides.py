import frappe
from frappe.core.doctype.user.user import User
from erpnext.setup.doctype.employee.employee import Employee

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

        self.name = str(start_from + count + 1)