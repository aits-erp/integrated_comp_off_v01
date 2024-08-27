# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import calendar
from datetime import datetime

from itertools import groupby
from operator import itemgetter


class ReprocessAttendance(Document):

	def before_cancel(self):
		
		#Cancel Attendance
		all_attendance = frappe.db.get_all("Attendance", {"custom_reprocess_reference": self.name})
		for rec in all_attendance:
			attendance = frappe.get_doc("Attandance", rec.name)
			if attendance.doctatus != 2:
				attendance.cancel()
				attendance.delete()
			else:
				frappe.throw(f"Can't Cancelled Already Cancelled Attandance {rec.name}")
		
		#Cancel Leave Allocation
		all_leave_allocation = frappe.db.get_all("Leave Allocation", {"custom_reprocess_reference": self.name})
		for rec in all_leave_allocation:
			leave_allocation = frappe.get_doc("Attandance", rec.name)
			if leave_allocation.docstatus != 2:
				leave_allocation.cancel()
				leave_allocation.delete()
			else:
				frappe.throw(f"Can't Cancelled Already Cancelled Leave Allocation {rec.name}")

		
		#Cancel Additional Salary
		all_additional_salary = frappe.db.get_all("Additional Salary", {"custom_reprocess_reference": self.name})
		for rec in all_additional_salary:
			additional_salary = frappe.get_doc("Attandance", rec.name)
			if additional_salary.docstatus != 2:
				additional_salary.cancel()
				additional_salary.delete()
			else:
				frappe.throw(f"Can't Cancelled Already Cancelled Leave Additional Salary {rec.name}")

	def before_submit(self):

		month_number = datetime.strptime(self.month, "%b").month

		fr_date = datetime(int(self.year), month_number, 1).date()
		t_date = datetime(int(self.year), month_number, calendar.monthrange(int(self.year), month_number)[1]).date()


		if self.employee != None:
			salary_slip = frappe.db.sql("""
				SELECT name FROM `tabSalary Slip` WHERE %s = start_date AND employee = %s
				""", (fr_date, self.employee), as_dict = 1)
			if salary_slip:
				frappe.throw(f"Salary Slip Found! (\n Month -> {self.start_date} \n Employee -> {employee} \n Salary Slip -> {str(salary_slip)}")
		else:
			salary_slip = frappe.db.sql("""
				SELECT name FROM `tabSalary Slip` WHERE %s = start_date
				""", (fr_date), as_dict = 1)
			if salary_slip:
				frappe.throw(f"Salary Slip Found! (\n Month -> {self.start_date} \n Salary Slip -> {str(salary_slip)}")
		
		

		x = frappe.call(
			"frappe.desk.query_report.run",
			report_name="Biometric Attendance Summary",
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

		for i in x.get("result"):
			i["attendance_date"] = str(i.get("date"))
			if i["in_time"] is None and i["out_time"] is None:
				continue
			elif i["attendance"] == "Missing In and Out":
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
			
				mark_attendance = r.get("attendance")
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

				if r.get("attendance") in ('Half Day'):
					half_type = "First Half"
					shift = frappe.get_doc("Shift Type", r.get("shift"))
					half_day_time = shift.start_time + shift.custom_half_day_threshold

					if r.get("in_time") > half_day_time:
						half_type = "Second Half"

				# attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": r.get("employee"), "attendance_date": r.get("attendance_date"), "docstatus": "1"})
				# for a in attendance_exists:
				# 	att = frappe.get_doc("Attendance", a.get("name"))
				# 	att.cancel()
				# 	att.delete()


				if not holiday_sql or mark_attendance in ('Half Day', 'Present'):

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

					previous_date = frappe.utils.add_to_date(attendance_date, days=-1)

					frappe.log_error('eerrrr', {
						"attendance_date": attendance_date,
						"previous_date": previous_date
					})

					self.process_compensation(previous_date, attendance_date, r.get("employee"))
					self.process_incentive(previous_date, attendance_date, r.get("employee"))

					# checkins = frappe.db.get_all("Employee Checkin", filters=[["Employee Checkin","employee","=",r.employee],["Employee Checkin","time","Between",[yesterday,yesterday]]])
					# for c in checkins:
					# 	print(c.name)
					# 	frappe.db.set_value("Employee Checkin", c.name, "attendance", attendance.name)


	def process_compensation(self, fr_date=None, t_date=None, employee=None):

		fr_date = f"{fr_date} 00:00:00"
		t_date = f"{t_date} 09:00:00"
		frappe.log_error('date fr anf to', {"fr_date": fr_date, "t_date": t_date})
		# employee = "50004"
		# holiday = frappe.db.get_value("Employee", employee, "holiday_list") #"Holiday List Plant 2024 - Sat"
		result = []
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
				0 holiday_flag
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
				-- AND '{fr_date}' <= ec.time
				-- AND ec.time <= '{t_date}'
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
					if g.custom_extra_work_hour == "Comp Off" or g.custom_present_on_holiday == "Comp Off":
						try:
							if data["in_time"] and data["out_time"] is None and sql[index+1]["in_time"] is None and sql[index+1]["out_time"]:
								data["out_time"] = sql[index+1]["out_time"]
								sql[index+1]["out_time"] = None
						
							if data["custom_end_across_days"] == 1 and data["in_time"] is not None and data["out_time"] is None:
								
								data["out_time"] = sql[index+1]["out_time"]
								sql[index+1]["out_time"] = None
						except Exception as e:
							msg = str(e)
				
				
						""" Fetching grade wise Present, Absent, HalfDay, late entry and early chekout Threshold """
						full_day = ""
						half_day = ""
						absent = ""
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
							if holiday_sql[0].holiday_date == data["date"]:
								data["holiday_flag"] = 1
							else:
								data["holiday_flag"] = 0  
						
						
						if data:
							result.append(data)
				
						
			filtered_result = []
			
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
		
			new_leaves_allocated = 0
			to_update_leave = 0
			# employee = ""
			
			if filtered_result:
				if filtered_result[0]["holiday_flag"] == 0:
					if len(filtered_result) > 1:
						slicer = 1
						employee = filtered_result[0]["employee"]
						identifier = frappe.db.get_value("Shift Type", filtered_result[0]["shift"], "identifier")
						extra_work = frappe.utils.get_timedelta("00:00:00")
						comp_off_validity = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_comp_off_validity")
						for result in filtered_result[slicer:]:
							extra_work = extra_work + result["worked_hours"]
						comp_matrix = frappe.get_doc("Compensation Matrix", identifier)
						if extra_work:
							for index, i in enumerate(comp_matrix.items):
								if i.get("from_hrs") <= extra_work <= i.get("to_hrs"):
									new_leaves_allocated = i.get("c_off_credit")
								else:
									if (index + 1) == len(comp_matrix.items):
										if extra_work > i.get("to_hrs"):
											new_leaves_allocated = i.get("c_off_credit")
						if new_leaves_allocated > 0:
							allocated_leaves_list = frappe.db.sql("""
								SELECT
									name
								FROM
									`tabLeave Allocation` la
								WHERE
									employee = %s
									AND (la.from_date BETWEEN %s AND %s or la.to_date BETWEEN %s AND %s)
									AND la.docstatus=1
									AND la.leave_type = 'Compensatory Off'
									AND la.new_leaves_allocated > 0
							""",(employee, t_date, frappe.utils.add_to_date(t_date, days=comp_off_validity), t_date, frappe.utils.add_to_date(t_date, days=comp_off_validity)), as_dict=True)
							if allocated_leaves_list:
								allocated_leaves = frappe.get_doc("Leave Allocation", allocated_leaves_list[0])
								frappe.log_error("existing log", allocated_leaves.as_json())
								# new_leaves_allocated = new_leaves_allocated + allocated_leaves.new_leaves_allocated
								to_update_leave = to_update_leave + allocated_leaves.new_leaves_allocated
								leave_app = frappe.db.sql("""
									SELECT
										SUM(lle.leaves) leaves
									FROM
										`tabLeave Ledger Entry` lle
									WHERE
										lle.employee = %s
										AND lle.from_date BETWEEN %s AND %s 
										AND lle.to_date BETWEEN %s AND %s
										AND lle.transaction_type = 'Leave Application'
										AND lle.leave_type = 'Compensatory Off'
										AND lle.leaves < 0
								""",(employee, allocated_leaves.from_date, allocated_leaves.to_date, allocated_leaves.from_date, allocated_leaves.to_date), as_dict=True)
								
								lv = leave_app[0]["leaves"] or 0
								if leave_app:
									to_update_leave = to_update_leave + lv
								
								if to_update_leave > 0:  
									comp_leave = frappe.get_doc(dict(
										doctype = "Compensation Leave Ledger",
										employee = employee,
										leave_from = allocated_leaves.from_date,
										leave_expiry = allocated_leaves.to_date,
										leave_count = allocated_leaves.new_leaves_allocated,
										status = "Active",
										reference_no = allocated_leaves.name
										))
									
									comp_leave.insert()
								
								# allocated_leaves.cancel()
								# allocated_leaves.delete()
								
								# leave_allocation_update = frappe.get_doc(dict(
								# 	doctype = "Leave Allocation",
								# 	employee = employee,
								# 	from_date = allocated_leaves.from_date,
								# 	to_date = frappe.utils.add_to_date(t_date, days=-1 ),
								# 	leave_type = "Compensatory Off",
								# 	new_leaves_allocated = to_update_leave,
								# 	custom_reprocess_reference=self.name
								# ))
								# frappe.log_error('leave_allocation_update', leave_allocation_update.as_json())
								# leave_allocation_update.insert()
								# leave_allocation_update.submit()

								
								frappe.throw(f"{allocated_leaves.to_date} == {fr_date}")
								if allocated_leaves.to_date == fr_date:
									# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "from_date",  )
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(fr_date, days=1))
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", allocated_leaves.new_leaves_allocated + to_update_leave)
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name)
								else:
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(allocated_leaves.from_date, days=-1 ))
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", to_update_leave )
									frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name )

								# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "from_date", allocated_leaves.from_date )
								# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(t_date, days=-1 ) )
								# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", to_update_leave )
								# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name )
								
								new_leaves_allocated = new_leaves_allocated + to_update_leave
								leave_allocation = frappe.get_doc(dict(
									doctype = "Leave Allocation",
									employee = employee,
									from_date = t_date,
									to_date = frappe.utils.add_to_date(t_date, days=comp_off_validity),
									leave_type = "Compensatory Off",
									new_leaves_allocated = new_leaves_allocated,
									custom_reprocess_reference=self.name
									))
								frappe.log_error("my_new_update_leave_allocation",leave_allocation )
								leave_allocation.insert()
								leave_allocation.submit()
							else:
								leave_allocation = frappe.get_doc(dict(
									doctype = "Leave Allocation",
									employee = employee,
									from_date = t_date,
									to_date = frappe.utils.add_to_date(t_date, days=comp_off_validity),
									leave_type = "Compensatory Off",
									new_leaves_allocated = new_leaves_allocated,
									custom_reprocess_reference=self.name
									))
								leave_allocation.insert()
								leave_allocation.submit()
						
				if filtered_result[0]["holiday_flag"] == 1:
					
					slicer = 0
					employee = filtered_result[0]["employee"]
					identifier = frappe.db.get_value("Shift Type", filtered_result[0]["shift"], "identifier")
					extra_work = frappe.utils.get_timedelta("00:00:00")
					comp_off_validity = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_comp_off_validity")
					for result in filtered_result[slicer:]:
						extra_work = extra_work + result["worked_hours"]
					comp_matrix = frappe.get_doc("Compensation Matrix", identifier)
					if extra_work:
						for index, i in enumerate(comp_matrix.items):
							
							if i.get("from_hrs") <= extra_work <= i.get("to_hrs"):
								new_leaves_allocated = i.get("c_off_credit")
							else:
								if (index + 1) == len(comp_matrix.items):
									if extra_work > i.get("to_hrs"):
										new_leaves_allocated = i.get("c_off_credit")
					if new_leaves_allocated > 0:
						allocated_leaves_list = frappe.db.sql("""
							SELECT
								name
							FROM
								`tabLeave Allocation` la
							WHERE
								employee = %s
								AND (la.from_date BETWEEN %s AND %s or la.to_date BETWEEN %s AND %s)
								AND la.docstatus=1
								AND la.leave_type = 'Compensatory Off'
								AND la.new_leaves_allocated > 0
						""",(employee, t_date, frappe.utils.add_to_date(t_date, days=comp_off_validity), t_date, frappe.utils.add_to_date(t_date, days=comp_off_validity)), as_dict=True)
						
						if allocated_leaves_list:
							allocated_leaves = frappe.get_doc("Leave Allocation", allocated_leaves_list[0])
							# new_leaves_allocated = new_leaves_allocated + allocated_leaves.new_leaves_allocated
							to_update_leave = to_update_leave + allocated_leaves.new_leaves_allocated
							leave_app = frappe.db.sql("""
								SELECT
									SUM(lle.leaves) leaves
								FROM
									`tabLeave Ledger Entry` lle
								WHERE
									lle.employee = %s
									AND lle.from_date BETWEEN %s AND %s 
									AND lle.to_date BETWEEN %s AND %s
									AND lle.transaction_type = 'Leave Application'
									AND lle.leave_type = 'Compensatory Off'
									AND lle.leaves < 0
							""",(employee, allocated_leaves.from_date, allocated_leaves.to_date, allocated_leaves.from_date, allocated_leaves.to_date), as_dict=True)
							
							lv = leave_app[0]["leaves"] or 0
							if leave_app:
								to_update_leave = to_update_leave + lv
							
							if to_update_leave > 0:  
								comp_leave = frappe.get_doc(dict(
									doctype = "Compensation Leave Ledger",
									employee = employee,
									leave_from = allocated_leaves.from_date,
									leave_expiry = allocated_leaves.to_date,
									leave_count = allocated_leaves.new_leaves_allocated,
									status = "Active",
									reference_no = allocated_leaves.name
									))
								
								comp_leave.insert()
							
							# allocated_leaves.cancel()
							# allocated_leaves.delete()
							
							# leave_allocation_update = frappe.get_doc(dict(
							# 	doctype = "Leave Allocation",
							# 	employee = employee,
							# 	from_date = allocated_leaves.from_date,
							# 	to_date = t_date, #to_be_checked
							# 	leave_type = "Compensatory Off",
							# 	new_leaves_allocated = to_update_leave,
							# 	custom_reprocess_reference=self.name
							# ))
							# frappe.log_error('leave_allocation_update513', leave_allocation_update.as_json())
							# leave_allocation_update.insert()
							# leave_allocation_update.submit()

							# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "from_date", allocated_leaves.from_date )
							# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(t_date, days=-1 ) )
							# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", to_update_leave )
							# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name )
							
							
							if allocated_leaves.to_date == fr_date:
								# frappe.db.set_value("Leave Allocation", allocated_leaves.name, "from_date",  )
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(fr_date, days=1))
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", allocated_leaves.new_leaves_allocated + to_update_leave)
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name)
							else:
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "to_date", frappe.utils.add_to_date(allocated_leaves.from_date, days=-1 ))
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "new_leaves_allocated", to_update_leave )
								frappe.db.set_value("Leave Allocation", allocated_leaves.name, "custom_reprocess_reference", self.name )

							
							new_leaves_allocated = new_leaves_allocated + to_update_leave
							leave_allocation = frappe.get_doc(dict(
								doctype = "Leave Allocation",
								employee = employee,
								from_date = t_date,
								to_date = frappe.utils.add_to_date(t_date, days=comp_off_validity),
								leave_type = "Compensatory Off",
								new_leaves_allocated = new_leaves_allocated,
								custom_reprocess_reference=self.name
								))
							leave_allocation.insert()
							leave_allocation.submit()
						else:
							leave_allocation = frappe.get_doc(dict(
								doctype = "Leave Allocation",
								employee = employee,
								from_date = t_date,
								to_date = frappe.utils.add_to_date(t_date, days=comp_off_validity),
								leave_type = "Compensatory Off",
								new_leaves_allocated = new_leaves_allocated,
								custom_reprocess_reference=self.name
								))
							leave_allocation.insert()
							leave_allocation.submit()

			
				
	def process_incentive(self, fr_date=None, t_date=None, employee=None):

		fr_date = f"{fr_date} 00:00:00"
		t_date = f"{t_date} 09:00:00"

		result = []
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
				0 holiday_flag
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
				-- AND '{fr_date}' <= ec.time
				-- AND ec.time <= '{t_date}'
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
							msg = str(e)
				
				
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
							if holiday_sql[0].holiday_date == data["date"]:
								data["holiday_flag"] = 1
							else:
								data["holiday_flag"] = 0    
						if data:
							result.append(data)
						
			filtered_result = []
			
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
			employee = ""
			extra_work = frappe.utils.get_timedelta("00:00:00")
			month_first_date = frappe.utils.get_first_day(fr_date)
			month_last_date = frappe.utils.get_last_day(fr_date)
			if len(filtered_result) > 0:
				if filtered_result[0]["holiday_flag"] == 0:
					if len(filtered_result) > 1:
						slicer = 1    
						employee = filtered_result[0]["employee"]
						incentive_gross = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_incentive_gross_amount") 
						incentive_ceiling = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_incentive_ceiling") 
						# frappe.get_doc("Employee Grade", filtered_result[0]["grade"])
						
						# employee = filtered_result[0]["employee"]
						identifier = frappe.db.get_value("Shift Type", filtered_result[0]["shift"], "identifier")
						
						salary_structure_assignment = frappe.db.get_list("Salary Structure Assignment", filters={"employee": employee}, order_by='creation desc')
						salary_structure_assignment_doc = frappe.get_doc("Salary Structure Assignment", salary_structure_assignment[0]["name"])
						salary_structure_doc = frappe.get_doc("Salary Structure", salary_structure_assignment_doc.salary_structure)
						gross = salary_structure_doc.total_earning
						
						if gross <= incentive_gross:
							
							for result in filtered_result[slicer:]:
								extra_work = extra_work + result["worked_hours"]
							# except Exception as e:
							#     msg = str(e)
							
							comp_matrix = frappe.get_doc("Compensation Matrix", identifier)
							if extra_work:
								for index, i in enumerate(comp_matrix.items):
									
									if i.get("from_hrs") <= extra_work <= i.get("to_hrs"):
										additional_incentive = (gross/frappe.utils.date_diff(month_last_date, month_first_date ) + 1) * i.get("c_off_credit")
									else:
										if (index + 1) == len(comp_matrix.items):
											if extra_work > i.get("to_hrs"):
												additional_incentive = (gross/frappe.utils.date_diff(month_last_date, month_first_date ) + 1) * i.get("c_off_credit")
												
												
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
									
									allocated_incentive = frappe.get_doc("Additional Salary", allocated_incentive_list[0]["name"])
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
											custom_reprocess_reference=self.name
											))
										incentive_allocation.insert()
										incentive_allocation.submit()
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
											custom_reprocess_reference=self.name
											))
										incentive_allocation.insert()
										incentive_allocation.submit()
										incentive_log_list = frappe.db.sql("""
											SELECT
												name
											FROM
												`tabIncentive Log` la
											WHERE
												employee = %s
												AND la.from_date = %s 
												AND la.to_date = %s
										""",(employee, month_first_date, month_last_date), as_dict=True)
										if incentive_log_list:
											# frappe.get_doc("Incentive Log", incentive_log_list[0])
											frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", additional_incentive - incentive_ceiling)
										else:    
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = extra
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
											custom_reprocess_reference=self.name
											))
										incentive_allocation.insert()
										incentive_allocation.submit()
											
									elif additional_incentive > incentive_ceiling:
										new_allocation = allocated_amount + (incentive_ceiling - allocated_amount)
										extra = additional_incentive - incentive_ceiling
										incentive_allocation = frappe.get_doc(dict(
											doctype = "Additional Salary",
											employee = employee,
											payroll_date = month_last_date,
											salary_component = "Incentives",
											amount = new_allocation,
											custom_reprocess_reference=self.name
											))
										incentive_allocation.insert()
										incentive_allocation.submit()
										incentive_log_list = frappe.db.sql("""
											SELECT
												name
											FROM
												`tabIncentive Log` la
											WHERE
												employee = %s
												AND la.from_date = %s 
												AND la.to_date = %s
										""",(employee, month_first_date, month_last_date), as_dict=True)
										if incentive_log_list:
											# frappe.get_doc("Incentive Log", incentive_log_list[0])
											frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", additional_incentive - incentive_ceiling)
										else:    
											incentive_log = frappe.get_doc(dict(
												doctype = "Incentive Log",
												employee = employee,
												from_date = month_first_date,
												to_date = month_last_date,
												leave_type = "Compensatory Off",
												incentive = extra
												))
								
											incentive_log.insert()
					
				if filtered_result[0]["holiday_flag"] == 1:
					
					slicer = 0    
					employee = filtered_result[0]["employee"]
					incentive_gross = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_incentive_gross_amount") 
					incentive_ceiling = frappe.db.get_value("Employee Grade", filtered_result[0]["grade"], "custom_incentive_ceiling") 
					# frappe.get_doc("Employee Grade", filtered_result[0]["grade"])
					
					# employee = filtered_result[0]["employee"]
					identifier = frappe.db.get_value("Shift Type", filtered_result[0]["shift"], "identifier")
					
					salary_structure_assignment = frappe.db.get_list("Salary Structure Assignment", filters={"employee": employee}, order_by='creation desc')
					salary_structure_assignment_doc = frappe.get_doc("Salary Structure Assignment", salary_structure_assignment[0]["name"])
					salary_structure_doc = frappe.get_doc("Salary Structure", salary_structure_assignment_doc.salary_structure)
					gross = salary_structure_doc.total_earning
					
					if gross <= incentive_gross:
						
						for result in filtered_result[slicer:]:
							extra_work = extra_work + result["worked_hours"]
						# except Exception as e:
						#     msg = str(e)
						
						comp_matrix = frappe.get_doc("Compensation Matrix", identifier)
						if extra_work:
							for index, i in enumerate(comp_matrix.items):
								
								if i.get("from_hrs") <= extra_work <= i.get("to_hrs"):
									additional_incentive = (gross/frappe.utils.date_diff(month_last_date, month_first_date ) + 1) * i.get("c_off_credit")
								else:
									if (index + 1) == len(comp_matrix.items):
										if extra_work > i.get("to_hrs"):
											additional_incentive = (gross/frappe.utils.date_diff(month_last_date, month_first_date ) + 1) * i.get("c_off_credit")
											
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
								
								allocated_incentive = frappe.get_doc("Additional Salary", allocated_incentive_list[0]["name"])
								additional_incentive = additional_incentive + allocated_incentive.amount
								
								if additional_incentive <= incentive_ceiling:
									allocated_incentive.cancel()
									allocated_incentive.delete()
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										amount = additional_incentive,
										custom_reprocess_reference=self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
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
										amount = new_allocation,
										custom_reprocess_reference=self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									incentive_log_list = frappe.db.sql("""
										SELECT
											name
										FROM
											`tabIncentive Log` la
										WHERE
											employee = %s
											AND la.from_date = %s 
											AND la.to_date = %s
									""",(employee, month_first_date, month_last_date), as_dict=True)
									if incentive_log_list:
										# frappe.get_doc("Incentive Log", incentive_log_list[0])
										frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", additional_incentive - incentive_ceiling)
									else:    
										incentive_log = frappe.get_doc(dict(
											doctype = "Incentive Log",
											employee = employee,
											from_date = month_first_date,
											to_date = month_last_date,
											leave_type = "Compensatory Off",
											incentive = extra
											))
							
										incentive_log.insert()
							else:
								if additional_incentive <= incentive_ceiling:
									incentive_allocation = frappe.get_doc(dict(
										doctype = "Additional Salary",
										employee = employee,
										payroll_date = month_last_date,
										salary_component = "Incentives",
										amount = additional_incentive,
										custom_reprocess_reference=self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									
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
										custom_reprocess_reference=self.name
										))
									incentive_allocation.insert()
									incentive_allocation.submit()
									incentive_log_list = frappe.db.sql("""
										SELECT
											name
										FROM
											`tabIncentive Log` la
										WHERE
											employee = %s
											AND la.from_date = %s 
											AND la.to_date = %s
									""",(employee, month_first_date, month_last_date), as_dict=True)
									if incentive_log_list:
										# frappe.get_doc("Incentive Log", incentive_log_list[0])
										frappe.db.set_value("Incentive Log", incentive_log_list[0], "incentive", additional_incentive - incentive_ceiling)
									else:    
										incentive_log = frappe.get_doc(dict(
											doctype = "Incentive Log",
											employee = employee,
											from_date = month_first_date,
											to_date = month_last_date,
											leave_type = "Compensatory Off",
											incentive = extra
											))
							
										incentive_log.insert()         

	
