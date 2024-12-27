# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.form.save import savedocs
from frappe.model.document import Document


class ReprocessAttendanceBulk(Document):
	
	def before_submit(self):
		company = self.company
		branch = self.branch
		division = self.division
		department = self.department
		employee = self.employee

		conditions = ""
		company_condition = ""
		branch_condition = ""
		division_condition = ""
		department_condition = ""
		employee_condition = ""

		if company:
			company_condition = f" and company = '{company}'"
		if branch:
			branch_condition = f" and branch = '{branch}'"
		if division:
			division_condition = f" and custom_division = '{division}'"
		if department:
			department_condition = f" and department = '{department}'"
		if employee:
			employee_condition = f" and employee = '{employee}'"

		conditions = f"{company_condition} {branch_condition} {division_condition} {department_condition} {employee_condition}"

		
		all_employee = frappe.db.sql(f"""
			SELECT 
				e.name
			FROM 
				`tabEmployee` e
			LEFT JOIN 
				`tabEmployee Grade` eg ON eg.name = e.grade
			WHERE
				status = 'Active' 
				AND eg.custom_single_punch_applicable = 0 
				AND eg.custom_no_punch_applicable = 0
				{conditions}
		""",(),as_dict=1)

		for rec in all_employee:
			reprocess_attendance = frappe.get_doc(dict(
					doctype="Reprocess Attendance",
					company=self.company,
					branch=self.branch,
					division=self.division,
					department=self.department,
					month=self.month,
					year=self.year,
					reprocess_attendance_bulk=self.name,
					employee=rec.name,
				))
			reprocess_attendance.save()
			savedocs(reprocess_attendance.as_json(), "Submit")

			# reprocess_attendance.submit()



