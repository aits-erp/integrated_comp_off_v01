# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import calendar
from datetime import datetime

from itertools import groupby
from operator import itemgetter


class ReprocessAttendance(Document):

	# def before_cancel(self):
		
	# 	#Cancel Attendance
	# 	all_attendance = frappe.db.get_all("Attendance", {"custom_reprocess_reference": self.name})
	# 	for rec in all_attendance:
	# 		attendance = frappe.get_doc("Attendance", rec.name)
	# 		if attendance.docstatus != 2:
	# 			attendance.cancel()
	# 			attendance.delete()
	# 		else:
	# 			frappe.throw(f"Cannot cancel already cancelled Attendance {rec.name}")
		
	# 	#Cancel Leave Allocation
	# 	all_leave_allocation = frappe.db.get_all("Leave Allocation", {"custom_reprocess_reference": self.name})
	# 	for rec in all_leave_allocation:
	# 		leave_allocation = frappe.get_doc("Attandance", rec.name)
	# 		if leave_allocation.docstatus != 2:
	# 			leave_allocation.cancel()
	# 			leave_allocation.delete()
	# 		else:
	# 			frappe.throw(f"Cannot cancel already cancelled Leave Allocation {rec.name}")

		
	# 	#Cancel Additional Salary
	# 	all_additional_salary = frappe.db.get_all("Additional Salary", {"custom_reprocess_reference": self.name})
	# 	for rec in all_additional_salary:
	# 		additional_salary = frappe.get_doc("Attandance", rec.name)
	# 		if additional_salary.docstatus != 2:
	# 			additional_salary.cancel()
	# 			additional_salary.delete()
	# 		else:
	# 			frappe.throw(f"Cannot cancel already cancelled Leave Additional Salary {rec.name}")

	def before_submit(self):
		
		month_number = datetime.strptime(self.month, "%b").month

		fr_date = datetime(int(self.year), month_number, 1).date()
		t_date = datetime(int(self.year), month_number, calendar.monthrange(int(self.year), month_number)[1]).date()
		
		if frappe.utils.get_first_day(self.modified) == fr_date:
			processed_till = frappe.utils.add_to_date(frappe.utils.getdate(frappe.utils.today()), days=-2)
		elif frappe.utils.get_first_day(self.modified) != fr_date:
			processed_till = t_date
		if self.employee != None:
			salary_slip = frappe.db.sql("""
				SELECT name FROM `tabSalary Slip` WHERE %s = start_date AND employee = %s AND docstatus in (0, 1)
				""", (fr_date, self.employee), as_dict = 1)
			if salary_slip:
				frappe.throw(f"Salary Slip Found! (\n Month -> {self.month} \n Employee -> {self.employee} \n Salary Slip -> {str(salary_slip)}")
		else:
			salary_slip = frappe.db.sql("""
				SELECT name FROM `tabSalary Slip` WHERE %s = start_date AND docstatus = docstatus in (0, 1)
				""", (fr_date), as_dict = 1)
			if salary_slip:
				frappe.throw(f"Salary Slip Found! (\n Month -> {self.month} \n Salary Slip -> {str(salary_slip)}")
		

		self.delete_attendance(fr_date, processed_till)
		self.delete_comp_leave_requests(fr_date, processed_till)
		self.delete_comp_leave_applications(fr_date, processed_till)
		self.delete_attendance_requests(fr_date, processed_till)
		# self.delete_comp_ledger(fr_date, t_date)
		self.delete_additional_salary(fr_date, t_date)
		self.delete_incentive_log(fr_date, t_date)

		x = frappe.call(
			"frappe.desk.query_report.run",
			report_name="Biometric Attendance Summary To Mark Attendance",
			filters={
				"company": self.company,
				"branch":self.branch,
				"month":self.month,
				"year":self.year,
				"employee":self.employee
			},
			ignore_prepared_report=True
		)


		filtered_result = []
		grade = frappe.db.get_value("Employee", self.employee, "grade")
		grade_doc = frappe.get_doc("Employee Grade", grade)
		filtered_result = []
		if grade_doc.custom_no_punch_applicable == 1:
			"""No Punch Employee"""
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
				company_condition = f" and e.company = '{company}'"
			if branch:
				branch_condition = f" and e.branch = '{branch}'"
			if division:
				division_condition = f" and e.custom_division = '{division}'"
			if department:
				department_condition = f" and e.department = '{department}'"
			if employee:
				employee_condition = f" and e.employee = '{employee}'"

			conditions = f"{company_condition} {branch_condition} {division_condition} {department_condition} {employee_condition}"
			
			start_date = frappe.utils.get_first_day(str(fr_date)) # frappe.utils.get_datetime("2024-06-01 00:00:00")
			end_date = processed_till
			current_date = start_date
			while current_date <= end_date:
		
				holiday_sql = frappe.db.sql(f"""
					SELECT
						(CASE WHEN h.weekly_off = 0 THEN "HO" ELSE "WO" END) AS holiday,
						-- (CASE WHEN h.weekly_off = 1 THEN "HO" ELSE 0 END) AS w_off,
						h.holiday_date
					FROM
						`tabHoliday List` hl
					LEFT JOIN
						`tabHoliday` h ON hl.name = h.parent
					WHERE
						hl.name = '{frappe.db.get_value("Employee", self.employee, "holiday_list")}'
						AND h.holiday_date = '{str(current_date)}'
					GROUP BY
						h.holiday_date
				""", as_dict = True)
				
				if len(holiday_sql) == 0:
					attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": self.employee, "attendance_date": current_date, "docstatus": "1"})
					for a in attendance_exists:
						att = frappe.get_doc("Attendance", a.get("name"))
						att.cancel()
						att.delete()
					count = frappe.db.count("Attendance", filters={"employee": self.employee, "attendance_date": current_date, "docstatus": 1})
					if count == 0:
						attendance = frappe.get_doc({
							"naming_series": "HR-ATT-.YYYY.-",
							"doctype": "Attendance",
							"employee": self.employee,
							"status": "Present",
							"attendance_date": str(current_date),
							"company": self.company,
							"custom_reprocess_reference": self.name
						})
						attendance.save()
						attendance.add_tag("No Check in Required")
						attendance.submit()
						
				current_date = frappe.utils.add_to_date(current_date, days=1)
		elif grade_doc.custom_single_punch_applicable == 1:
			"""Single Punch Employee"""
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
				company_condition = f" and e.company = '{company}'"
			if branch:
				branch_condition = f" and e.branch = '{branch}'"
			if division:
				division_condition = f" and e.custom_division = '{division}'"
			if department:
				department_condition = f" and e.department = '{department}'"
			if employee:
				employee_condition = f" and e.employee = '{employee}'"

			conditions = f"{company_condition} {branch_condition} {division_condition} {department_condition} {employee_condition}"

			start_date = frappe.utils.get_first_day(str(fr_date)) # frappe.utils.get_datetime("2024-06-01 00:00:00")
			end_date = processed_till
			
			current_date = start_date
			while current_date <= end_date:
			
				# st = frappe.utils.nowdate() + " " + "00:00:00"
				# et = frappe.utils.nowdate() + " " + "23:59:59"
				st = str(current_date) + " " + "00:00:00"
				et = str(current_date) + " " + "23:59:59"
			
				checkin_sql = frappe.db.sql("""
					SELECT
						ec.name
					FROM
						`tabEmployee Checkin` ec
					WHERE
						ec.employee = %s
						AND ec.time BETWEEN %s AND %s
					GROUP BY
						ec.name
				""", (self.employee, st, et), as_dict = True)
				if len(checkin_sql) > 0:
					holiday_sql = frappe.db.sql(f"""
						SELECT
							(CASE WHEN h.weekly_off = 0 THEN "HO" ELSE "WO" END) AS holiday,
							-- (CASE WHEN h.weekly_off = 1 THEN "HO" ELSE 0 END) AS w_off,
							h.holiday_date
						FROM
							`tabHoliday List` hl
						LEFT JOIN
							`tabHoliday` h ON hl.name = h.parent
						WHERE
							hl.name = '{frappe.db.get_value("Employee", self.employee, "holiday_list")}'
							AND h.holiday_date = '{str(current_date)}'
						GROUP BY
							h.holiday_date
					""", as_dict = True)
					if len(holiday_sql) == 0:
						attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": self.employee, "attendance_date": current_date, "docstatus": "1"})
						for a in attendance_exists:
							att = frappe.get_doc("Attendance", a.get("name"))
							att.cancel()
							att.delete()
						count = frappe.db.count("Attendance", filters={"employee": self.employee, "attendance_date": current_date, "docstatus": 1})
						if count == 0:
							attendance = frappe.get_doc({
								"naming_series": "HR-ATT-.YYYY.-",
								"doctype": "Attendance",
								"employee": self.employee,
								"status": "Present",
								"attendance_date": current_date,
								"company": self.company,
								"custom_reprocess_reference": self.name
							})
							attendance.save()
							attendance.add_tag("Single Check in Required")
							attendance.submit()
				else:
					holiday_sql = frappe.db.sql(f"""
						SELECT
							(CASE WHEN h.weekly_off = 0 THEN "HO" ELSE "WO" END) AS holiday,
							-- (CASE WHEN h.weekly_off = 1 THEN "HO" ELSE 0 END) AS w_off,
							h.holiday_date
						FROM
							`tabHoliday List` hl
						LEFT JOIN
							`tabHoliday` h ON hl.name = h.parent
						WHERE
							hl.name = '{frappe.db.get_value("Employee", self.employee, "holiday_list")}'
							AND h.holiday_date = '{str(current_date)}'
						GROUP BY
							h.holiday_date
					""", as_dict = True)
					if len(holiday_sql) == 0:
						attendance = frappe.get_doc({
							"naming_series": "HR-ATT-.YYYY.-",
							"doctype": "Attendance",
							"employee": self.employee,
							"status": "Absent",
							"attendance_date": current_date,
							"company": self.company,
							"custom_reprocess_reference": self.name
						})
						attendance.save()
						attendance.add_tag("Single Check in Required")
						attendance.submit()
				current_date = frappe.utils.add_to_date(current_date, days=1)	

		elif not x.get("result"):

			"""Marking absent with no checkin for general employee"""
			cur_date = fr_date
			emp_grade = frappe.db.get_value("Employee", self.employee, "grade")
			is_active = frappe.db.get_value("Employee", self.employee, "status")
			emp_grade_doc = frappe.get_doc("Employee Grade", emp_grade)
			date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
			if is_active == "Active":
				if  emp_grade_doc.custom_no_punch_applicable == 0 or emp_grade_doc.custom_single_punch_applicable == 0:
					while cur_date <= t_date:
						attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": self.employee, "attendance_date": cur_date, "docstatus": "1"})
						for a in attendance_exists:
							att = frappe.get_doc("Attendance", a.get("name"))
							att.cancel()
							att.delete()
						if not attendance_exists:
							if date_of_joining <= frappe.utils.getdate(cur_date) and frappe.utils.getdate(cur_date) <= processed_till:
								attendance = frappe.new_doc("Attendance")
								holiday_sql = frappe.db.sql(f"""
									SELECT
										h.name, h.holiday_date, h.weekly_off
									FROM
										`tabHoliday List` hl
									LEFT JOIN
										`tabHoliday` h ON hl.name = h.parent
									WHERE
										hl.name = '{frappe.db.get_value("Employee", self.employee, "holiday_list")}'
										AND h.holiday_date = '{cur_date}'
									GROUP BY
										h.holiday_date
								""", as_dict = True)
								if not holiday_sql:
									attendance.update(
										{
											"doctype": "Attendance",
											"employee": self.employee,
											"attendance_date": cur_date,
											"status": "Absent",
											"custom_attendance_tag": "No Punch Data",
											# "custom_half_type": half_type,
											# "custom_reason": r.get("attendance"),
											# "shift": r.get("shift"),
											# "late_entry": 1 if r.get("late_entry") == 'Yes' else 0,
											# "early_exit": 1 if r.get("early_exit") == 'Yes' else 0,
											"custom_reprocess_reference": self.name
										}
									).save()
									attendance.submit()
						cur_date = frappe.utils.add_to_date(cur_date, days=1)
		else:
			"""Processing Checkin Data"""
			for i in x.get("result"):
				i["attendance_date"] = str(i.get("date"))
				if i["in_time"] is None and i["out_time"] is None:
					continue
				elif i.get("attendance") == "Missing In and Out" or i.get("attendance") == "Not Present":
					continue
				else:
					filtered_result.append(i)
			
			filtered_result.sort(key=itemgetter('employee'))
			for key, group in groupby(filtered_result, key=itemgetter('employee')):
				ssa = frappe.db.count("Salary Structure Assignment", filters = {"employee": key, "docstatus": 1})
				if ssa == 0:
					frappe.throw(f"Salary Structure Assignment! Not Found For (Employee -> {key} )")

				grouped = {}
				for item in group:
					date = item["attendance_date"]
					if date not in grouped:
						grouped[date] = item

				inner_filtered_result = list(grouped.values())
				start_date = fr_date
				end_date = t_date

				missing_dates = []

				current_date = start_date
				while current_date <= end_date:
					missing_dates.append({"attendance_date": str(current_date), "attendance": "Absent", "employee": key})
					current_date += frappe.utils.get_timedelta("24:00:00")

				merged_dict = {item["attendance_date"]: item for item in missing_dates + inner_filtered_result}

				merged_list = list(merged_dict.values())
				for r in merged_list:
					holiday_sql = frappe.db.sql(f"""
						SELECT
							h.name, h.holiday_date, h.weekly_off
						FROM
							`tabHoliday List` hl
						LEFT JOIN
							`tabHoliday` h ON hl.name = h.parent
						WHERE
							hl.name = '{frappe.db.get_value("Employee", r.get("employee"), "holiday_list")}'
							AND h.holiday_date = '{r.get("attendance_date")}'
						GROUP BY
							h.holiday_date
					""", as_dict = True)

					attendance_tag = ""

					
					# if r.get("attendance") == 'POH' or r.get("attendance") == 'POW':
					# 	mark_attendance = 'Present'
					if r.get("attendance") is None or r.get('attendance') == '':
						mark_attendance = 'Absent'
					else:	
						mark_attendance = r.get("attendance")
						#attendance_tag = "l"
					attendance_date = r.get("attendance_date")

					if holiday_sql and r.get("attendance") in ('Present', 'Half Day', 'Absent'):
						if holiday_sql[0].weekly_off == 1:
							attendance_tag = "POW"

						if holiday_sql[0].weekly_off == 0:
							attendance_tag = "POH"

					if r.get("attendance") in ('Absent','Missing In', 'Missing Out', 'Invalid Punch'):
						mark_attendance = 'Absent'
						attendance_tag = ""

					half_type = ""
					if r.get("attendance") is not None:
						if r.get("attendance") in ('Half Day'):
							half_type = "First Half"
							shift = frappe.get_doc("Shift Type", r.get("shift"))
							half_day_time = shift.start_time + shift.custom_half_day_threshold

							if r.get("in_time") > half_day_time:
								half_type = "Second Half"

					if frappe.utils.getdate(attendance_date) <= processed_till:
						attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": r.get("employee"), "attendance_date": r.get("attendance_date"), "docstatus": "1"})
						for a in attendance_exists:
							att = frappe.get_doc("Attendance", a.get("name"))
							att.cancel()
							att.delete()
					
					if frappe.utils.getdate(self.creation) > frappe.utils.getdate(attendance_date):
						if (not holiday_sql or mark_attendance in ('Half Day', 'Present')) and attendance_tag not in ("POH", "POW"):
							date_of_joining = frappe.db.get_value("Employee", r.get("employee"), "date_of_joining")
							if date_of_joining <= frappe.utils.getdate(attendance_date) and frappe.utils.getdate(attendance_date) <= processed_till:
								attendance_exists_for_the_day = frappe.db.get_all("Attendance", filters={"employee": r.get("employee"), "attendance_date": attendance_date})
								if not attendance_exists_for_the_day:
									attendance = frappe.new_doc("Attendance")
									attendance.update(
										{
											"doctype": "Attendance",
											"employee": r.get("employee"),
											"attendance_date": attendance_date,
											"status": mark_attendance,
											"custom_attendance_tag": attendance_tag,
											"custom_half_type": half_type,
											"custom_reason": r.get("attendance"),
											"shift": r.get("shift"),
											"late_entry": 1 if r.get("late_entry") == 'Yes' else 0,
											"early_exit": 1 if r.get("early_exit") == 'Yes' else 0,
											"custom_reprocess_reference": self.name
										}
									).save()
									attendance.submit()

					next_date = frappe.utils.add_to_date(attendance_date, days=+1)

					
					self.process_compensation(self.company, self.branch, self.month, self.year, r.get("employee"), filtered_result)
					if frappe.utils.getdate(attendance_date) <= processed_till:
						self.process_incentive(attendance_date, next_date, r.get("employee"))

					# checkins = frappe.db.get_all("Employee Checkin", filters=[["Employee Checkin","employee","=",r.employee],["Employee Checkin","time","Between",[yesterday,yesterday]]])
					# for c in checkins:
					# 	print(c.name)
					# 	frappe.db.set_value("Employee Checkin", c.name, "attendance", attendance.name)

	def delete_attendance(self, fr_date=None, t_date=None):
		frappe.db.sql(f"""
			DELETE
			FROM `tabAttendance`
			WHERE attendance_date BETWEEN '{fr_date}' AND '{t_date}'
			AND employee = '{self.employee}'
		""", as_dict=True)
		frappe.db.commit()

	def delete_comp_leave_requests(self, fr_date=None, t_date=None):
		employee = ""
		emp_cond = f" and employee = '{self.employee}'" if self.employee else ""
		conditions = f"{emp_cond}"

		all_comp_leave_requests = frappe.db.sql(f"""
			SELECT ar.name
			FROM `tabCompensatory Leave Request` ar 
			WHERE 1=1
			{conditions}
			AND work_from_date BETWEEN '{fr_date}' AND '{t_date}'
			AND ar.docstatus = 1
			AND ar.leave_type = 'Compensatory Off'
		""", (), as_dict=True)	

		
		if all_comp_leave_requests:
			for a in all_comp_leave_requests:
				a_doc = frappe.get_doc("Compensatory Leave Request", a.get("name"))
				if a_doc.docstatus == 1:
					a_doc.cancel()
					frappe.db.set_value("Compensatory Leave Request", a.get("name"), "status", "Cancelled")
					frappe.db.commit()
					a_doc.delete()
				else:
					a_doc.delete()

	def delete_comp_leave_applications(self, fr_date=None, t_date=None):
		employee = ""
		emp_cond = f" and employee = '{self.employee}'" if self.employee else ""
		conditions = f"{emp_cond}"

		all_comp_leave_applications = frappe.db.sql(f"""
			SELECT ar.name
			FROM `tabLeave Application` ar 
			WHERE 1=1
			{conditions}
			AND from_date BETWEEN %s AND %s
			AND to_date BETWEEN %s AND %s
			AND ar.docstatus = 1
			AND ar.leave_type = 'Compensatory Off'
		""", (fr_date, t_date, fr_date, t_date), as_dict=True)		

		if all_comp_leave_applications:
			for a in all_comp_leave_applications:
				a_doc = frappe.get_doc("Leave Application", a.get("name"))
				if a_doc.docstatus == 1:
					a_doc.cancel()
					frappe.db.set_value("Leave Application", a.get("name"), "status", "Cancelled")
					frappe.db.set_value("Leave Application", a.get("name"), "workflow_state", "Cancelled")
					frappe.db.commit()
					# a_doc.delete()
				# else:
				# 	a_doc.delete()

	def delete_attendance_requests(self, fr_date=None, t_date=None):
		employee = ""
		emp_cond = f" and ar.employee = '{self.employee}'" if self.employee else ""
		conditions = f"{emp_cond}"

		all_attendance_requests = frappe.db.sql(f"""
			SELECT ar.name
			FROM `tabAttendance Request` ar 
			WHERE 1=1
			{conditions}
			AND from_date BETWEEN '{fr_date}' AND '{t_date}'
			AND to_date BETWEEN '{fr_date}' AND '{t_date}'
			AND ar.docstatus = 1
		""", (), as_dict=True)
		

		if all_attendance_requests:
			for a in all_attendance_requests:
				a_doc = frappe.get_doc("Attendance Request", a.get("name"))
				if a_doc.docstatus == 1:
					a_doc.cancel()
					frappe.db.set_value("Attendance Request", a.get("name"), "status", "Cancelled")
					frappe.db.set_value("Attendance Request", a.get("name"), "workflow_state", "Cancelled")
					frappe.db.commit()

	def delete_additional_salary(self, fr_date=None, t_date=None):
		employee = ""
		emp_cond = f" and employee = '{self.employee}'" if self.employee else ""
		conditions = f"{emp_cond}"

		frappe.db.sql(f"""
			DELETE
			FROM `tabAdditional Salary` 
			WHERE 1=1
			{conditions}
			AND payroll_date BETWEEN %s AND %s
			AND docstatus = 1 
			AND salary_component = "Incentives"
			AND type = "Earning"
		""", (fr_date, t_date), as_dict=True)

		frappe.db.commit()

	def delete_incentive_log(self, fr_date=None, t_date=None):
		employee = ""
		emp_cond = f" and employee = '{self.employee}'" if self.employee else ""
		conditions = f"{emp_cond}"

		frappe.db.sql(f"""
			DELETE
			FROM `tabIncentive Log` 
			WHERE 1=1
			{conditions}
			AND from_date BETWEEN %s AND %s
			AND to_date BETWEEN %s AND %s
		""", (fr_date, t_date, fr_date, t_date), as_dict=True)

		frappe.db.commit()


	def process_compensation(self,company, branch, month, year, employee, filtered_result):
		extra_work_dict = {}

		for i in filtered_result:
			work_shift = i.get("shift")
			identifier = str(frappe.db.get_value("Shift Type", i.get("shift"), "identifier"))
			grade = frappe.db.get_value("Employee", i.get("employee"), "grade")
			worked_hours = i.get("worked_hours") if i.get("worked_hours") else frappe.utils.get_timedelta("00:00:00") 
			if worked_hours > frappe.utils.get_timedelta("00:00:00"):
				if (i.get("employee") + "--" + str(i.get("date")) + "--" + grade) in extra_work_dict:
					extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade]["worked_hours"] = extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade]["worked_hours"] + worked_hours
				if (i.get("employee") + "--" + str(i.get("date")) + "--" + grade) not in extra_work_dict:
					extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade] = {"worked_hours": worked_hours, "identifier": identifier, "date": i.get("date"), "employee": i.get("employee")}
		for ew in extra_work_dict:
			new_leaves_allocated = 0
			work = ew.split("--")
			work_emp = work[0]
			work_date = work[1]
				# "0" + work[2]
			emp_grade = frappe.get_doc("Employee Grade", work[2])
			matrix_id = extra_work_dict[ew]["identifier"]
			if len(matrix_id) == 7:
				matrix_id = "0" + matrix_id
			comp_matrix = frappe.get_doc("Compensation Matrix", matrix_id)
			comp_off_validity = emp_grade.custom_comp_off_validity #frappe.db.get_value("Employee Grade", emp_grade, "custom_comp_off_validity")
			holiday_list = frappe.get_doc("Holiday List", frappe.db.get_value("Employee", work_emp, "holiday_list"))
			all_holidays = [x.get("holiday_date") for x in holiday_list.holidays]
			actual_work = frappe.utils.get_timedelta("00:00:00")
			status = ""
			
			for h in holiday_list.holidays:
				if h.holiday_date == frappe.utils.getdate(work_date):
					if h.weekly_off == 1:
						status = "POW"
					elif h.weekly_off == 0:
						status = "POH"
				
			if frappe.utils.getdate(work_date) in all_holidays:
				if emp_grade.custom_present_on_holiday == "Comp Off":
					actual_work = actual_work + extra_work_dict[ew]["worked_hours"]
					
			else:
				if emp_grade.custom_extra_work_hour == "Comp Off":
					actual_work = extra_work_dict[ew]["worked_hours"] - frappe.utils.get_timedelta(extra_work_dict[ew]["identifier"]) # frappe.utils.get_timedelta(str(identifier))
					status = "EW"
			if actual_work > frappe.utils.get_timedelta("00:00:00"):
				for index, i in enumerate(comp_matrix.items):
					if i.get("from_hrs") <= actual_work <= i.get("to_hrs"):
						new_leaves_allocated = i.get("c_off_credit")
						
					if (index + 1) == len(comp_matrix.items):
							if actual_work > i.get("to_hrs"):
								new_leaves_allocated = i.get("c_off_credit")
				if new_leaves_allocated > 0:
					comp_lv_req_exist = frappe.db.get_all("Compensatory Leave Request", filters={"employee": work_emp, "work_from_date": frappe.utils.add_to_date(work_date, days=0), "work_end_date": frappe.utils.add_to_date(work_date, days=0)})
					date_of_joining = frappe.db.get_value("Employee", work_emp, "date_of_joining")
					if frappe.utils.get_first_day(work_date) == frappe.utils.get_first_day(self.modified):
						if frappe.utils.add_to_date(frappe.utils.getdate(self.modified), days=-2) >= frappe.utils.getdate(work_date):
							if not comp_lv_req_exist and date_of_joining <= frappe.utils.getdate(work_date):
								comp_lv_req = frappe.get_doc(dict(
									doctype = "Compensatory Leave Request",
									employee = work_emp,
									leave_type = "Compensatory Off",
									work_from_date = frappe.utils.add_to_date(work_date, days=0),
									work_end_date = frappe.utils.add_to_date(work_date, days=0),
									expiry = frappe.utils.add_to_date(work_date, days=comp_off_validity),
									credit = new_leaves_allocated,
									status = status + str(actual_work),
									reason = status
									))

								comp_lv_req.insert()
								comp_lv_req.submit()
					if frappe.utils.get_first_day(work_date) != frappe.utils.get_first_day(self.modified):
						if not comp_lv_req_exist and date_of_joining <= frappe.utils.getdate(work_date):
							comp_lv_req = frappe.get_doc(dict(
								doctype = "Compensatory Leave Request",
								employee = work_emp,
								leave_type = "Compensatory Off",
								work_from_date = frappe.utils.add_to_date(work_date, days=0),
								work_end_date = frappe.utils.add_to_date(work_date, days=0),
								expiry = frappe.utils.add_to_date(work_date, days=comp_off_validity),
								credit = new_leaves_allocated,
								status = status + str(actual_work),
								reason = status
								))

							comp_lv_req.insert()
							comp_lv_req.submit()

	def process_incentive(self, fr_date=None, t_date=None, employee=None):

		fr_date = f"{fr_date} 00:00:00"
		t_date = f"{t_date} 10:30:00"
		cur_t_date = t_date
		
		result = []
		filtered_result = []
		sql = frappe.db.sql(f"""
			SELECT
				e.name AS employee,
				e.employee_name,
				e.holiday_list,
				DATE(ec.time) AS date,
				(CASE WHEN ec.log_type = 'IN' THEN TIME(ec.time) END) AS in_time,
				(CASE WHEN ec.log_type = 'OUT' THEN TIME(ec.time) END) AS out_time,
				
				MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END) AS in_date_time,
				MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END) AS out_date_time,
				
				TIME(st.start_time) AS shift_start_time,
				TIME(st.end_time) AS shift_end_time,
				ec.shift,
				e.grade,
				-- (CASE WHEN sa.start_date BETWEEN '{fr_date}' AND '{t_date}' AND sa.employee = e.name THEN sa.name ELSE e.default_shift END) AS shift,
				CASE WHEN st.custom_end_across_days = 1 THEN st.custom_end_across_days ELSE 0 END as custom_end_across_days,
				CASE WHEN ec.custom_is_temporary_shift = 1 THEN "Yes" ELSE "No" END as custom_is_temporary_shift,
				0 is_holiday,
				e.holiday_list
			FROM
				`tabEmployee` AS e
			LEFT JOIN
				`tabEmployee Checkin` AS ec ON e.name = ec.employee
			LEFT JOIN
				`tabShift Type` AS st ON st.name = ec.shift
			LEFT JOIN
				`tabShift Assignment` AS sa ON sa.employee = e.name
			WHERE
				ec.time BETWEEN '{fr_date}' AND '{t_date}'
				AND e.name = '{employee}'
			GROUP BY
				e.name, ec.time
			ORDER BY
				ec.time ASC
		""", as_dict=True)
		
		if sql:
			
			for index, data in enumerate(sql):
			
				if data["grade"]:
					g = frappe.get_doc("Employee Grade", data["grade"])
					if g.custom_extra_work_hour == "Incentive" or g.custom_present_on_holiday == "Incentive":
						try:
							if data["in_time"] and data["out_time"] is None and sql[index+1]["in_time"] is None and sql[index+1]["out_time"]:
								data["out_time"] = sql[index+1]["out_time"]
								sql[index+1]["out_time"] = None
						
							if data["custom_end_across_days"] == 1 and data["in_time"] is not None and data["out_time"] is None:
								
								data["out_time"] = sql[index+1]["out_time"]
								sql[index+1]["out_time"] = None
						except Exception as e:
							msg = e
							
							
						""" Fetching grade wise Present, Absent, HalfDay, late entry and early chekout Threshold """
						grade_emp = None
						if data["grade"]:
							grade_emp = frappe.get_doc("Employee Grade", data["grade"])
						
						if grade_emp:        
							#full_day = frappe.utils.get_time(grade_emp.custom_present_threshold_hrs)
							#half_day = frappe.utils.get_time(grade_emp.custom_half_day_threshold_hrs)
							#absent = frappe.utils.get_time(grade_emp.custom_absent_threshold_hrs)
							if grade_emp.custom_check_in_grace_time is not None:
								fifteen_minutes_in = frappe.utils.get_time(grade_emp.custom_check_in_grace_time) or frappe.utils.get_time("00:00:00")
							if grade_emp.custom_check_out_grace_time is not None:
								fifteen_minutes_out = frappe.utils.get_time(grade_emp.custom_check_out_grace_time) or frappe.utils.get_time("00:00:00")
							late_count_threshold = grade_emp.custom_allowed_late_count_days or 0
						
						if data["shift"]:
							shift = frappe.get_doc("Shift Type", data["shift"])
							full_day = frappe.utils.get_time(shift.custom_present_threshold)
							half_day = frappe.utils.get_time(shift.custom_half_day_threshold)
							absent = frappe.utils.get_time(shift.custom_absent_threshold)
							st = shift.start_time
							et = shift.end_time
						shift_type = ""
						if data["shift"]:
							shift_type = frappe.get_doc("Shift Type", data["shift"])
						
						""" Marking Attendance and Checkin """
						
						hours = frappe.utils.get_timedelta("00:00:00")
						if data["out_time"] is None and data["in_time"] is None:
							data["attendance"] = "Missing In and Out"
						elif data["in_time"] is None and data["out_time"]:
							data["attendance"] = "Missing In"
						elif data["out_time"] is None and data["in_time"]:
							data["attendance"] = "Missing Out"
						elif data["out_time"] is None:
							data["attendance"] = "Missing Out"
						elif data["out_time"] < data["in_time"] and data["custom_end_across_days"] != 1:
							data["attendance"] = "Invalid Punch"
						elif data["out_time"] > data["in_time"]:
							hours = data["out_time"] - data["in_time"]
							data["worked_hours"] = hours
							if frappe.utils.get_time(hours) >= full_day:
								data["attendance"] = "Present"
							elif full_day >= frappe.utils.get_time(hours) >= half_day:
								data["attendance"] = "Half Day"
							elif frappe.utils.get_time(hours) < absent:
								data["attendance"] = "Absent"
								
						elif data["out_time"] < data["in_time"] and data["custom_end_across_days"] == 1:
							twenty_four_hour = frappe.utils.get_timedelta("24:00:00")
							hours = data["out_time"] + twenty_four_hour - data["in_time"]
							data["worked_hours"] = hours
							if frappe.utils.get_time(hours) >= full_day:
								data["attendance"] = "Present"
							elif full_day >= frappe.utils.get_time(hours) >= half_day:
								data["attendance"] = "Half Day"
							elif frappe.utils.get_time(hours) < absent:
								data["attendance"] = "Absent"
						
						holiday_sql = frappe.db.sql(f"""
							SELECT
								h.weekly_off,
								h.holiday_date
							FROM
								`tabHoliday List` hl
							LEFT JOIN
								`tabHoliday` h ON hl.name = h.parent
							WHERE
								hl.name = '{data.get("holiday_list")}'
								AND h.holiday_date = '{fr_date}'
							GROUP BY
								h.holiday_date
						""", as_dict = True)
						if holiday_sql:
							data["weekly_off"] = holiday_sql[0].get("weekly_off")
							if str(data["date"]) == str(holiday_sql[0].get("holiday_date")):
								data["is_holiday"] = 1
							
						if data:
							result.append(data)
						
			
			
			for i in result:
				if i["in_time"] is None and i["out_time"] is None:
					continue
				elif i["attendance"] == "Missing In and Out":
					continue
				elif i["attendance"] == "Missing In":
					continue
				elif i["attendance"] == "Missing Out":
					continue
				else:
					filtered_result.append(i)
					
			additional_incentive = 0
			actual = 0
			employee = ""
			extra_work = frappe.utils.get_timedelta("00:00:00")
			month_first_date = frappe.utils.get_first_day(fr_date)
			month_last_date = frappe.utils.get_last_day(fr_date)
			slicer = 0
			if filtered_result:
				extra_work_dict = {}

				for i in filtered_result:
					if i.get("date") == frappe.utils.getdate(cur_t_date):
						continue
					work_shift = i.get("shift")
					identifier = str(frappe.db.get_value("Shift Type", i.get("shift"), "identifier"))
					grade = frappe.db.get_value("Employee", i.get("employee"), "grade")
					worked_hours = i.get("worked_hours") if i.get("worked_hours") else frappe.utils.get_timedelta("00:00:00") 
					if worked_hours > frappe.utils.get_timedelta("00:00:00"):
						if (i.get("employee") + "--" + str(i.get("date")) + "--" + grade) in extra_work_dict:
							extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade]["worked_hours"] = extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade]["worked_hours"] + worked_hours
						if (i.get("employee") + "--" + str(i.get("date")) + "--" + grade) not in extra_work_dict:
							extra_work_dict[i.get("employee") + "--" + str(i.get("date")) + "--" + grade] = {"worked_hours": worked_hours, "identifier": identifier, "date": i.get("date"), "employee": i.get("employee")}
				for ew in extra_work_dict:
					new_leaves_allocated = 0
					work = ew.split("--")
					employee = work[0]
					work_date = work[1]
						# "0" + work[2]
					emp_grade = frappe.get_doc("Employee Grade", work[2])
					matrix_id = extra_work_dict[ew]["identifier"]
					if len(matrix_id) == 7:
						matrix_id = "0" + matrix_id
					comp_matrix = frappe.get_doc("Compensation Matrix", matrix_id)
					incentive_gross = emp_grade.custom_incentive_gross_amount # frappe.db.get_value("Employee Grade", emp_grade, "custom_incentive_gross_amount") 
					incentive_ceiling = emp_grade.custom_incentive_ceiling # frappe.db.get_value("Employee Grade", emp_grade, "custom_incentive_ceiling")
					comp_off_validity = emp_grade.custom_comp_off_validity #frappe.db.get_value("Employee Grade", emp_grade, "custom_comp_off_validity")
					salary_structure_assignment = frappe.db.get_list("Salary Structure Assignment", filters={"employee": employee}, order_by='creation desc')
					holiday_list = frappe.get_doc("Holiday List", frappe.db.get_value("Employee", employee, "holiday_list"))
					all_holidays = [x.get("holiday_date") for x in holiday_list.holidays]
					actual_work = frappe.utils.get_timedelta("00:00:00")
					status = ""
					date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
					if date_of_joining <= frappe.utils.getdate(frappe.utils.add_to_date(t_date, days=-1)):
						if len(salary_structure_assignment) > 0:
							salary_structure_assignment_doc = frappe.get_doc("Salary Structure Assignment", salary_structure_assignment[0]["name"])
							salary_structure_doc = frappe.get_doc("Salary Structure", salary_structure_assignment_doc.salary_structure)
							gross = salary_structure_doc.total_earning

							for h in holiday_list.holidays:
								if h.holiday_date == frappe.utils.getdate(work_date):
									if h.weekly_off == 1:
										status = "POW"
									elif h.weekly_off == 0:
										status = "POH"
								
							if frappe.utils.getdate(work_date) in all_holidays:
								if emp_grade.custom_present_on_holiday == "Incentive":
									actual_work = actual_work + extra_work_dict[ew]["worked_hours"]
									extra_work = actual_work
									
							else:
								if emp_grade.custom_extra_work_hour == "Incentive":
									actual_work = extra_work_dict[ew]["worked_hours"] - frappe.utils.get_timedelta(extra_work_dict[ew]["identifier"]) # frappe.utils.get_timedelta(str(identifier))
									extra_work = actual_work
									status = "EW"

							for index, i in enumerate(comp_matrix.items):
								
								if i.get("from_hrs") <= extra_work <= i.get("to_hrs"):
									additional_incentive = (gross/(frappe.utils.date_diff(month_last_date, month_first_date ) + 1)) * i.get("c_off_credit")
									actual = (gross/(frappe.utils.date_diff(month_last_date, month_first_date ) + 1)) * i.get("c_off_credit")
								
								else:
									if (index + 1) == len(comp_matrix.items):
										if extra_work > i.get("to_hrs"):
											additional_incentive = (gross/(frappe.utils.date_diff(month_last_date, month_first_date ) + 1)) * i.get("c_off_credit")
											actual = (gross/(frappe.utils.date_diff(month_last_date, month_first_date ) + 1)) * i.get("c_off_credit")
											
						if additional_incentive > 0:
							allocated_incentive_list = frappe.db.sql("""
								SELECT
									name
								FROM
									`tabAdditional Salary` la
								WHERE
									employee = %s
									AND (la.payroll_date BETWEEN %s AND %s) 
									AND la.salary_component = 'Incentives'
									AND la.docstatus=1
							""",(employee, month_first_date, month_last_date), as_dict=True)
							
							allocated_amount = 0
							if allocated_incentive_list:
								allocated_incentive = frappe.get_doc("Additional Salary", allocated_incentive_list[0].get("name"))
								additional_incentive = additional_incentive + allocated_incentive.amount
								
								if additional_incentive <= incentive_ceiling:
									allocated_incentive.cancel()
									allocated_incentive.delete()
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										leave_type = "Compensatory Off",
										amount = additional_incentive,
										custom_reprocess_reference = self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
									if not exist:
										incentive_log = frappe.get_doc(dict(
											doctype = "Incentive Log",
											employee = employee,
											from_date = month_first_date,
											to_date = month_last_date,
											leave_type = "Compensatory Off",
											incentive = actual,
											work_date = frappe.utils.add_to_date(t_date, days=-1),
											status = status
											))
							
										incentive_log.insert()                                    
								elif additional_incentive > incentive_ceiling:
									allocated_incentive.cancel()
									allocated_incentive.delete()
									new_allocation = allocated_amount + (incentive_ceiling - allocated_amount)
									extra = additional_incentive - incentive_ceiling
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										leave_type = "Compensatory Off",
										amount = new_allocation,
										custom_reprocess_reference = self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									incentive_log_list = frappe.db.sql("""
										SELECT
											name,
											sum(incentive) cur
										FROM
											`tabIncentive Log` la
										WHERE
											employee = %s
											AND la.from_date = %s 
											AND la.to_date = %s
									""",(employee, month_first_date, month_last_date), as_dict=True)
									if incentive_log_list:
										# frappe.get_doc("Incentive Log", incentive_log_list[0])
										# cur = frappe.db.get_value("Incentive Log", incentive_log_list[0], "incentive")
										# frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", cur + (additional_incentive - incentive_ceiling))
										exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
										if not exist:
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = actual,
												total_incentive = (incentive_log_list[0].get("cur") or 0) + (additional_incentive - incentive_ceiling),
												work_date = frappe.utils.add_to_date(t_date, days=-1),
												status = status
												))
								
											incentive_log.insert()
									else:
										exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
										if not exist:
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = actual,
												total_incentive = actual,
												work_date = frappe.utils.add_to_date(t_date, days=-1),
												status = status
												))
								
											incentive_log.insert()
							else:
								if additional_incentive <= incentive_ceiling:
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										leave_type = "Compensatory Off",
										amount = additional_incentive,
										custom_reprocess_reference = self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
									if not exist:
										incentive_log = frappe.get_doc(dict(
											doctype = "Incentive Log",
											employee = employee,
											from_date = month_first_date,
											to_date = month_last_date,
											leave_type = "Compensatory Off",
											incentive = actual,
											total_incentive = additional_incentive,
											work_date = frappe.utils.add_to_date(t_date, days=-1),
											status = status
											))
							
										incentive_log.insert()
										
								elif additional_incentive > incentive_ceiling:
									new_allocation = allocated_amount + (incentive_ceiling - allocated_amount)
									extra = additional_incentive - incentive_ceiling
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										leave_type = "Compensatory Off",
										amount = new_allocation,
										custom_reprocess_reference = self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									incentive_log_list = frappe.db.sql("""
										SELECT
											name,
											sum(incentive) cur
										FROM
											`tabIncentive Log` la
										WHERE
											employee = %s
											AND la.from_date = %s 
											AND la.to_date = %s
									""",(employee, month_first_date, month_last_date), as_dict=True)
									if incentive_log_list:
										# frappe.get_doc("Incentive Log", incentive_log_list[0])
										# cur = frappe.db.get_value("Incentive Log", incentive_log_list[0], "incentive")
										# frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", cur + (additional_incentive - incentive_ceiling))
										
										exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
										if not exist:
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = actual,
												total_incentive = (incentive_log_list[0].get("cur") or 0) + (additional_incentive - incentive_ceiling),
												work_date = frappe.utils.add_to_date(t_date, days=-1),
												status = status
												))
											
											incentive_log.insert()
											
									else:
										exist = frappe.db.get_all("Incentive Log", filters={"employee": employee, "from_date": month_first_date,
																				"to_date": month_last_date, 
																				"work_date": frappe.utils.add_to_date(t_date, days=-1)})
										if not exist:
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = actual,
												total_incentive = actual,
												work_date = frappe.utils.add_to_date(t_date, days=-1),
												status = status
												))
								
											incentive_log.insert()
				# except Exception as e:
				# 	msg = str(e)        
				# 	frappe.log_error("msg", msg)
	