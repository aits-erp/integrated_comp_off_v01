# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReprocessAttendance(Document):
	pass
	# def before_save(self):
	# 	# attendance_for_date = frappe.utils.getdate()

	# 	year = str(self.year)
	# 	month = str(self.month)
	# 	employee_code = self.employee
	# 	holiday_list = ""
	# 	company = self.company
	# 	branch = self.branch
	# 	division = self.division
	# 	department = self.department

	# 	conditions = ""
	# 	emp_condition = ""
	# 	company_condition = ""
	# 	branch_condition = ""
	# 	division_condition = ""
	# 	department_condition = ""

	# 	if employee_code:
	# 		emp_condition = f" and e.name = '{employee_code}'"
	# 	if company:
	# 		company_condition = f" and e.company = '{company}'"
	# 	if branch:
	# 		branch_condition = f" and e.branch = '{branch}'"
	# 	if division:
	# 		division_condition = f" and e.custom_division = '{division}'"
	# 	if department:
	# 		department_condition = f" and e.department = '{department}'"

	# 	conditions = f"{emp_condition} {company_condition} {branch_condition} {division_condition} {department_condition}"

	# 	result = []

	# 	month_days = {
	# 		"Jan": {"from_date": "12-31", "to_date": "02-01"},
	# 		"Feb": {"from_date": "01-31", "to_date": "03-01"},
	# 		"Mar": {"from_date": "02-28", "to_date": "04-01"},
	# 		"Apr": {"from_date": "03-31", "to_date": "05-01"},
	# 		"May": {"from_date": "04-30", "to_date": "06-01"},
	# 		"Jun": {"from_date": "05-31", "to_date": "07-01"},
	# 		"Jul": {"from_date": "06-30", "to_date": "08-01"},
	# 		"Aug": {"from_date": "07-31", "to_date": "09-01"},
	# 		"Sep": {"from_date": "08-31", "to_date": "10-01"},
	# 		"Oct": {"from_date": "09-30", "to_date": "11-01"},
	# 		"Nov": {"from_date": "10-31", "to_date": "12-01"},
	# 		"Dec": {"from_date": "11-30", "to_date": "01-01"}
	# 	}

	# 	fr_date = ""
	# 	t_date = ""
	# 	first_day_next_month = ""
	# 	first_day_last_month = ""
	# 	if month and year:
	# 		if month in month_days:
	# 			fr_date = str(year) + "-" + month_days[month]["from_date"] + " " + "00:00:00"
	# 			t_date = str(year) + "-" + month_days[month]["to_date"] + " " + "23:59:59"
	# 			first_day_next_month = str(year) + "-" + month_days[month]["to_date"]
	# 			first_day_last_month = str(year) + "-" + month_days[month]["from_date"]

	# 	employee_list = frappe.db.sql(f"""
	# 		SELECT
	# 			DISTINCT e.name, e.employee_name
	# 		FROM
	# 			`tabEmployee` e
	# 		LEFT JOIN `tabEmployee Grade` g ON g.name = e.grade
	# 		WHERE
	# 			e.status = 'Active'
	# 			AND g.custom_single_punch_applicable = 0
	# 			AND g.custom_no_punch_applicable = 0
	# 		""", as_dict=True)

	# 	for emp in employee_list:    
	# 		sql = frappe.db.sql(f"""
	# 			SELECT
	# 				e.name AS employee,
	# 				e.employee_name,
	# 				e.holiday_list,
	# 				DATE(ec.time) AS date,
	# 				(CASE WHEN ec.log_type = 'IN' THEN TIME(ec.time) END) AS in_time,
	# 				(CASE WHEN ec.log_type = 'OUT' THEN TIME(ec.time) END) AS out_time,
					
	# 				MIN(CASE WHEN ec.log_type = 'IN' THEN ec.time END) AS in_date_time,
	# 				MAX(CASE WHEN ec.log_type = 'OUT' THEN ec.time END) AS out_date_time,
					
	# 				TIME(st.start_time) AS shift_start_time,
	# 				TIME(st.end_time) AS shift_end_time,
	# 				ec.shift,
	# 				(CASE WHEN ec.log_type = 'IN' THEN ec.device_id END) as in_device,
	# 				(CASE WHEN ec.log_type = 'OUT' THEN ec.device_id END) as out_device,
	# 				(CASE WHEN ec.log_type = 'IN' THEN ec.custom_area END) as in_area,
	# 				(CASE WHEN ec.log_type = 'OUT' THEN ec.custom_area END) as out_area,
	# 				e.grade,
	# 				-- (CASE WHEN sa.start_date BETWEEN '{fr_date}' AND '{t_date}' AND sa.employee = e.name THEN sa.name ELSE e.default_shift END) AS shift,
	# 				CASE WHEN st.custom_end_across_days = 1 THEN st.custom_end_across_days ELSE 0 END as custom_end_across_days,
	# 				CASE WHEN ec.custom_is_temporary_shift = 1 THEN "Yes" ELSE "No" END as custom_is_temporary_shift
	# 			FROM
	# 				`tabEmployee` AS e
	# 			LEFT JOIN
	# 				`tabEmployee Checkin` AS ec ON e.name = ec.employee
	# 			LEFT JOIN
	# 				`tabShift Type` AS st ON st.name = ec.shift
	# 			LEFT JOIN
	# 				`tabShift Assignment` AS sa ON sa.employee = e.name
	# 			LEFT JOIN
	# 	        	`tabEmployee Grade` AS eg ON eg.name = e.grade
	# 			WHERE
	# 				1=1
	# 				{conditions}
	# 				AND ec.time BETWEEN '{fr_date}' AND '{t_date}'
	# 				-- AND '{fr_date}' <= ec.time
	# 				-- AND ec.time <= '{t_date}'
	# 				AND e.name = '{emp["name"]}'
	# 				AND eg.custom_single_punch_applicable = 0
	# 	        	AND eg.custom_no_punch_applicable = 0
	# 			GROUP BY
	# 				e.name, ec.time
	# 			ORDER BY
	# 				ec.time ASC
	# 		""", as_dict=True)
			
			
				
	# 		full_day = frappe.utils.get_time("08:00:00")
	# 		half_day = frappe.utils.get_time("04:00:00")
	# 		absent = frappe.utils.get_time("04:00:00")
	# 		fifteen_minutes_in = frappe.utils.get_time("00:00:00")
	# 		fifteen_minutes_out = frappe.utils.get_time("00:00:00")
	# 		consecutive_late_entries = {}
			
	# 		if sql:
				
	# 			for index, data in enumerate(sql):
	# 				# frappe.log_error(title="first_data", message=data)
	# 				try:
	# 					if data["in_time"] and data["out_time"] is None and sql[index+1]["in_time"] is None and sql[index+1]["out_time"]:
	# 						data["out_time"] = sql[index+1]["out_time"]
	# 						data["out_area"] = sql[index+1]["out_area"]
	# 						data["out_device"] = sql[index+1]["out_device"]
	# 						sql[index+1]["out_time"] = None
					
	# 					if data["custom_end_across_days"] == 1 and data["in_time"] is not None and data["out_time"] is None:
							
	# 						data["out_time"] = sql[index+1]["out_time"]
	# 						sql[index+1]["out_time"] = None
	# 				except Exception as e:
	# 					msg = str(e)

	# 				""" Fetching grade wise Present, Absent, HalfDay, late entry and early chekout Threshold """
	# 				grade_emp = None
	# 				if data["grade"]:
	# 					grade_emp = frappe.get_doc("Employee Grade", data["grade"])
					
	# 				if grade_emp:        
	# 					#full_day = frappe.utils.get_time(grade_emp.custom_present_threshold_hrs)
	# 					#half_day = frappe.utils.get_time(grade_emp.custom_half_day_threshold_hrs)
	# 					#absent = frappe.utils.get_time(grade_emp.custom_absent_threshold_hrs)
	# 					if grade_emp.custom_check_in_grace_time is not None:
	# 						fifteen_minutes_in = frappe.utils.get_time(grade_emp.custom_check_in_grace_time) or frappe.utils.get_time("00:00:00")
	# 					if grade_emp.custom_check_out_grace_time is not None:
	# 						fifteen_minutes_out = frappe.utils.get_time(grade_emp.custom_check_out_grace_time) or frappe.utils.get_time("00:00:00")
	# 					late_count_threshold = grade_emp.custom_allowed_late_count_days or 0
					
					
	# 				"""SHIFT START TIME AND END TIME FULL DAY HALF DAY ABSENT THRESHOLD"""
					
					
	# 				if data["shift"]:
	# 					shift = frappe.get_doc("Shift Type", data["shift"])
	# 					full_day = frappe.utils.get_time(shift.custom_present_threshold)
	# 					half_day = frappe.utils.get_time(shift.custom_half_day_threshold)
	# 					absent = frappe.utils.get_time(shift.custom_absent_threshold)
	# 					st = shift.start_time
	# 					et = shift.end_time
					
					
	# 				data["shift_start_time"] = st
	# 				data["shift_end_time"] = et
	# 				shift_type = ""
	# 				if data["shift"]:
	# 					shift_type = frappe.get_doc("Shift Type", data["shift"])
					
	# 				""" Handling across days shifts / night shift """
					
					
				
							
	# 				""" Marking Attendance and Checkin """
					
	# 				hours = frappe.utils.get_timedelta("00:00:00")
	# 				if data["out_time"] is None and data["in_time"] is None:
	# 					data["attendance"] = "Missing In and Out"
	# 				elif data["in_time"] is None and data["out_time"]:
	# 					data["attendance"] = "Missing In"
	# 				elif data["out_time"] is None and data["in_time"]:
	# 					data["attendance"] = "Missing Out"
	# 				elif data["out_time"] is None:
	# 					data["attendance"] = "Missing Out"
	# 				elif data["out_time"] < data["in_time"] and data["custom_end_across_days"] != 1:
	# 					data["attendance"] = "Invalid Punch"
	# 				elif data["out_time"] > data["in_time"]:
	# 					hours = data["out_time"] - data["in_time"]
	# 					data["worked_hours"] = hours
	# 					if frappe.utils.get_time(hours) >= full_day:
	# 						data["attendance"] = "Present"
	# 					elif full_day >= frappe.utils.get_time(hours) >= half_day:
	# 						data["attendance"] = "Half Day"
	# 					elif frappe.utils.get_time(hours) < absent:
	# 						data["attendance"] = "Absent"
							
	# 				elif data["out_time"] < data["in_time"] and data["custom_end_across_days"] == 1:
	# 					twenty_four_hour = frappe.utils.get_timedelta("24:00:00")
	# 					hours = data["out_time"] + twenty_four_hour - data["in_time"]
	# 					data["worked_hours"] = hours
	# 					if frappe.utils.get_time(hours) >= full_day:
	# 						data["attendance"] = "Present"
	# 					elif full_day >= frappe.utils.get_time(hours) >= half_day:
	# 						data["attendance"] = "Half Day"
	# 					elif frappe.utils.get_time(hours) < absent:
	# 						data["attendance"] = "Absent"
						
				
	# 				""" Marking Late Chekin """
	# 				late_count = frappe.db.get_value("Employee Grade", data["grade"], "custom_allowed_late_count_days") or 3
					
	# 				if data["shift_start_time"] and data["in_time"]:
	# 					if str(data["date"]) > first_day_last_month:
							
	# 						late_entry_difference = data["in_time"] - data["shift_start_time"]
	# 						late_entry_difference_seconds = late_entry_difference.total_seconds()
	# 						f_seconds = fifteen_minutes_in.hour * 3600 + fifteen_minutes_in.minute * 60 + fifteen_minutes_in.second
							
	# 						if 0 < late_entry_difference_seconds < f_seconds :
	# 							data["late_entry"] = "Yes"
	# 							employee = str(data["employee"]) + str(data["date"]) 
	# 							date = data["date"]
								
	# 							if employee not in consecutive_late_entries:
	# 								consecutive_late_entries[employee] = consecutive_late_entries.get(employee, 0) + 1
	# 								#consecutive_late_entries[date] = consecutive_late_entries.get(date, 0) + 1
								
	# 								if len(consecutive_late_entries) > late_count:
	# 									if absent > frappe.utils.get_time(hours) > frappe.utils.get_time("00:00:00"):
	# 										data["attendance"] = "Absent"
	# 									elif data["out_time"] is None and data["in_time"]:
	# 										data["attendance"] = "Missing Out"
	# 									else:
	# 										data["attendance"] = "Half Day"
							
	# 						elif late_entry_difference_seconds > f_seconds:
	# 							if data["in_time"] and data["out_time"]:
	# 								data["attendance"] = "Half Day"
	# 								data["late_entry"] = "Yes"
	# 							elif data["in_time"]:
	# 								data["late_entry"] = "Yes"
									
	# 						else:
	# 							data["late_entry"] = "No"
	# 							#consecutive_late_entries[data["employee"]] = 0
					
	# 				""" Marking Early Checkout """
					
	# 				if data["shift_end_time"] and data["out_time"]:
	# 					early_exit_difference = data["shift_end_time"] - data["out_time"]
	# 					early_exit_difference_seconds = early_exit_difference.total_seconds()
	# 					f_seconds = fifteen_minutes_out.hour * 3600 + fifteen_minutes_out.minute * 60 + fifteen_minutes_out.second
	# 					if early_exit_difference_seconds > f_seconds :
	# 						data["early_exit"] = "Yes"
	# 					else:
	# 						data["early_exit"] = "No"
				
	# 				"""Checking in area and out area"""
	# 				if data["in_area"] and data["out_area"]:
	# 					if data["in_area"] != data["out_area"]:
	# 						data["area_change"] = "Yes"
	# 					if data["in_area"] == data["out_area"]:
	# 						data["area_change"] = "No"
					
	# 				if str(data["date"]) != first_day_next_month and str(data["date"]) != first_day_last_month:
	# 					result.append(data)
	# 					# frappe.log_error(title="final_data", message=data)
			
	# 	filtered_result = []

	# 	for i in result:
	# 		i["attendance_date"] = str(i.get("date"))
	# 		if i["in_time"] is None and i["out_time"] is None:
	# 			continue
	# 		elif i["attendance"] == "Missing In and Out":
	# 			continue
	# 		else:
	# 			filtered_result.append(i)

	# 	grouped = {}
	# 	for item in filtered_result:
	# 		date = item["attendance_date"]
	# 		if date not in grouped:
	# 			grouped[date] = item

	# 	filtered_result = list(grouped.values())

	# 	start_date = frappe.utils.get_first_day(attendance_for_date)
	# 	end_date = attendance_for_date

	# 	missing_dates = []

	# 	current_date = start_date
	# 	while current_date <= end_date:
	# 		missing_dates.append({"attendance_date": str(current_date), "attendance": "Absent"})
	# 		current_date += frappe.utils.get_timedelta("24:00:00")

	# 	merged_dict = {item["attendance_date"]: item for item in missing_dates + filtered_result}

	# 	merged_list = list(merged_dict.values())

	# 	for r in merged_list:

	# 		holiday_sql = frappe.db.sql(f"""
	# 			SELECT
	# 				h.holiday_date
	# 			FROM
	# 				`tabHoliday List` hl
	# 			LEFT JOIN
	# 				`tabHoliday` h ON hl.name = h.parent
	# 			WHERE
	# 				hl.name = '{holiday_list}'
	# 				AND h.holiday_date = '{r.get("attendance_date")}'
	# 			GROUP BY
	# 				h.holiday_date
	# 		""", as_dict = True)


	# 		if not holiday_sql:			
			
	# 			mark_attendance = r.get("attendance")
	# 			attendance_date = r.get("attendance_date")

	# 			if r.get("attendance") in ('Absent','Missing In', 'Missing Out', 'Invalid Punch'):
	# 				mark_attendance = 'Absent'


	# 			attendance_exists = frappe.db.get_all("Attendance", filters={"employee": employee_code, "attendance_date": r.get("attendance_date"), "docstatus": "1"})
	# 			print(employee_code, mark_attendance, attendance_date)
	# 			if not attendance_exists:

	# 				attendance = frappe.new_doc("Attendance")
	# 				attendance.update(
	# 					{
	# 						"doctype": "Attendance",
	# 						"employee": employee_code,
	# 						"attendance_date": attendance_date,
	# 						"status": mark_attendance,
	# 						"custom_reason": r.get("attendance"),
	# 						"shift": r.get("shift"),
	# 						"late_entry": 1 if r.get("late_entry") == 'Yes' else 0,
	# 						"early_exit": 1 if r.get("early_exit") == 'Yes' else 0
	# 					}
	# 				).save()
	# 				# attendance.submit()

	# 				# checkins = frappe.db.get_all("Employee Checkin", filters=[["Employee Checkin","employee","=",r.employee],["Employee Checkin","time","Between",[yesterday,yesterday]]])
	# 				# for c in checkins:
	# 				# 	print(c.name)
	# 				# 	frappe.db.set_value("Employee Checkin", c.name, "attendance", attendance.name)


	# 	frappe.throw("Before SUbimit validation")
