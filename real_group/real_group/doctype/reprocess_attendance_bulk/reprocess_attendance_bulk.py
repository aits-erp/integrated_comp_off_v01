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
				-- AND eg.custom_single_punch_applicable = 0 
				-- AND eg.custom_no_punch_applicable = 0
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
					custom_state="In Progress"
				))
			reprocess_attendance.save()
			# savedocs(reprocess_attendance.as_json(), "Submit")

			# reprocess_attendance.submit()

	# 	frappe.enqueue(self.process_attendance_from_no_check_in_applicable_grade(), queue='long')
	# 	frappe.enqueue(self.process_attendance_from_single_check_in_applicable_grade(), queue='long')
		
	
	# def process_attendance_from_no_check_in_applicable_grade(self):

	# 	company = self.company
	# 	branch = self.branch
	# 	division = self.division
	# 	department = self.department
	# 	employee = self.employee

	# 	conditions = ""
	# 	company_condition = ""
	# 	branch_condition = ""
	# 	division_condition = ""
	# 	department_condition = ""
	# 	employee_condition = ""

	# 	if company:
	# 		company_condition = f" and e.company = '{company}'"
	# 	if branch:
	# 		branch_condition = f" and e.branch = '{branch}'"
	# 	if division:
	# 		division_condition = f" and e.custom_division = '{division}'"
	# 	if department:
	# 		department_condition = f" and e.department = '{department}'"
	# 	if employee:
	# 		employee_condition = f" and e.employee = '{employee}'"

	# 	conditions = f"{company_condition} {branch_condition} {division_condition} {department_condition} {employee_condition}"
		
	# 	month_number = datetime.strptime(self.month, "%b").month
	# 	fr_date = datetime(int(self.year), month_number, 1).date()
	# 	t_date = datetime(int(self.year), month_number, calendar.monthrange(int(self.year), month_number)[1]).date()
	# 	start_date = frappe.utils.get_first_day(str(fr_date)) # frappe.utils.get_datetime("2024-06-01 00:00:00")
	# 	end_date = frappe.utils.get_last_day(str(fr_date))
	# 	current_date = start_date
	# 	while current_date <= end_date:
	# 		employees = frappe.db.sql(f"""
	# 			SELECT 
	# 				e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company, e.holiday_list
	# 			FROM `tabEmployee` e
	# 			LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
	# 			LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
	# 			WHERE g.custom_no_punch_applicable = 1
	# 			AND e.status = 'Active'
	# 			{conditions}
				
	# 		""", as_dict=True)
			
	# 		if employees:

	# 			for e in employees:
	# 				holiday_sql = frappe.db.sql(f"""
	# 					SELECT
	# 						(CASE WHEN h.weekly_off = 0 THEN "HO" ELSE "WO" END) AS holiday,
	# 						-- (CASE WHEN h.weekly_off = 1 THEN "HO" ELSE 0 END) AS w_off,
	# 						h.holiday_date
	# 					FROM
	# 						`tabHoliday List` hl
	# 					LEFT JOIN
	# 						`tabHoliday` h ON hl.name = h.parent
	# 					WHERE
	# 						hl.name = '{e["holiday_list"]}'
	# 						AND h.holiday_date = '{str(current_date)}'
	# 					GROUP BY
	# 						h.holiday_date
	# 				""", as_dict = True)
					
	# 				if len(holiday_sql) == 0:
	# 					attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": e.name, "attendance_date": current_date, "docstatus": "1"})
	# 					for a in attendance_exists:
	# 						att = frappe.get_doc("Attendance", a.get("name"))
	# 						att.cancel()
	# 						att.delete()
	# 					count = frappe.db.count("Attendance", filters={"employee": e.name, "attendance_date": current_date, "docstatus": 1})
	# 					if count == 0:
	# 						attendance = frappe.get_doc({
	# 							"naming_series": "HR-ATT-.YYYY.-",
	# 							"doctype": "Attendance",
	# 							"employee": e.name,
	# 							"status": "Present",
	# 							"attendance_date": str(current_date),
	# 							"company": e.company,
	# 						})
	# 						attendance.save()
	# 						attendance.add_tag("No Check in Required")
	# 						attendance.submit()
							
	# 			current_date = frappe.utils.add_to_date(current_date, days=1)

	# def process_attendance_from_single_check_in_applicable_grade(self):

	# 	company = self.company
	# 	branch = self.branch
	# 	division = self.division
	# 	department = self.department
	# 	employee = self.employee

	# 	conditions = ""
	# 	company_condition = ""
	# 	branch_condition = ""
	# 	division_condition = ""
	# 	department_condition = ""
	# 	employee_condition = ""

	# 	if company:
	# 		company_condition = f" and e.company = '{company}'"
	# 	if branch:
	# 		branch_condition = f" and e.branch = '{branch}'"
	# 	if division:
	# 		division_condition = f" and e.custom_division = '{division}'"
	# 	if department:
	# 		department_condition = f" and e.department = '{department}'"
	# 	if employee:
	# 		employee_condition = f" and e.employee = '{employee}'"

	# 	conditions = f"{company_condition} {branch_condition} {division_condition} {department_condition} {employee_condition}"

	# 	month_number = datetime.strptime(self.month, "%b").month
	# 	fr_date = datetime(int(self.year), month_number, 1).date()
	# 	t_date = datetime(int(self.year), month_number, calendar.monthrange(int(self.year), month_number)[1]).date()
	# 	start_date = frappe.utils.get_first_day(str(fr_date)) # frappe.utils.get_datetime("2024-06-01 00:00:00")
	# 	end_date = frappe.utils.get_last_day(str(fr_date))
		
	# 	current_date = start_date
	# 	while current_date <= end_date:
	# 		employees = frappe.db.sql(f"""
	# 			SELECT 
	# 				e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company, e.holiday_list
	# 			FROM `tabEmployee` e
	# 			LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
	# 			LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
	# 			WHERE g.custom_single_punch_applicable = 1
	# 			AND e.status = 'Active'
	# 			{conditions}
	# 		""", as_dict=True)

	# 		if employees:
	# 			# st = frappe.utils.nowdate() + " " + "00:00:00"
	# 			# et = frappe.utils.nowdate() + " " + "23:59:59"
	# 			st = str(current_date) + " " + "00:00:00"
	# 			et = str(current_date) + " " + "23:59:59"
	# 			for e in employees:
	# 				checkin_sql = frappe.db.sql("""
	# 					SELECT
	# 						ec.name
	# 					FROM
	# 						`tabEmployee Checkin` ec
	# 					WHERE
	# 						ec.employee = %s
	# 						AND ec.time BETWEEN %s AND %s
	# 					GROUP BY
	# 						ec.name
	# 				""", (e.name, st, et), as_dict = True)
	# 				if len(checkin_sql) > 0:
	# 					holiday_sql = frappe.db.sql(f"""
	# 						SELECT
	# 							(CASE WHEN h.weekly_off = 0 THEN "HO" ELSE "WO" END) AS holiday,
	# 							-- (CASE WHEN h.weekly_off = 1 THEN "HO" ELSE 0 END) AS w_off,
	# 							h.holiday_date
	# 						FROM
	# 							`tabHoliday List` hl
	# 						LEFT JOIN
	# 							`tabHoliday` h ON hl.name = h.parent
	# 						WHERE
	# 							hl.name = '{e["holiday_list"]}'
	# 							AND h.holiday_date = '{str(current_date)}'
	# 						GROUP BY
	# 							h.holiday_date
	# 					""", as_dict = True)
	# 					if len(holiday_sql) == 0:
	# 						count = frappe.db.count("Attendance", filters={"employee": e.name, "attendance_date": current_date, "docstatus": 1})
	# 						if count == 0:
	# 							attendance = frappe.get_doc({
	# 								"naming_series": "HR-ATT-.YYYY.-",
	# 								"doctype": "Attendance",
	# 								"employee": e.name,
	# 								"status": "Present",
	# 								"attendance_date": current_date,
	# 								"company": e.company,
	# 							})
	# 							attendance.save()
	# 							attendance.add_tag("Single Check in Required")
	# 							attendance.submit()
	# 			current_date = frappe.utils.add_to_date(current_date, days=1)	



