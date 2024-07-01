import frappe
from frappe.utils import get_timedelta, get_datetime, add_to_date


@frappe.whitelist()
def process_attendance_log():
	attendance_logs = frappe.db.sql(
		"""
		SELECT 
			*
		FROM
			bio_attendance_log
		WHERE is_processed = 'N'
		AND LENGTH(employee_id) >= 5
		ORDER by employee_id, punch_date, punch_time
		LIMIT 500
	""", as_dict=True)

	for log in attendance_logs:

		try:

			if not frappe.db.exists("Employee", log.employee_id):
				sql = f"UPDATE bio_attendance_log set is_processed = 'E', message = 'Employee ID Does not exists' where name = '{log.name}'"
				frappe.db.sql(sql)
			else:
				log_type = ""
				time = f"{log.punch_date} {log.punch_time}"
				
				if log.punch_direction == "I":
					log_type = "IN" 

				if log.punch_direction == "O":
					log_type = "OUT"


				# check shift from employee master

				shift = frappe.db.get_value("Employee", log.employee_id, "default_shift") 

				## check shift from employee grade master
				employee_grade = frappe.db.get_value("Employee", log.employee_id, "grade")

				if employee_grade:

					grade = frappe.get_doc("Employee Grade", employee_grade)
					grade_shifts = [shift.shift for shift in grade.custom_allowed_shifts]
					
					if grade_shifts:
						for g in grade_shifts:
							shift_start_time, shift_end_time, cross_days = frappe.db.get_value("Shift Type", g, ["start_time", "end_time", "custom_end_across_days"])
							shift_start_time = f"{log.punch_date} {str(shift_start_time)}"
							shift_end_time = f"{add_to_date(log.punch_date, days=cross_days)} {str(shift_end_time)}"
							buffer_shift_start_time = get_datetime(shift_start_time) - get_timedelta("00:30:00")
							buffer_shift_end_time = get_datetime(shift_end_time) - get_timedelta("00:30:00")

							# print((get_timedelta("24:00:00") - get_timedelta(log.punch_time) <buffer_shift_end_time , buffer_shift_start_time), log.punch_time, shift_start_time, shift_end_time, buffer_shift_start_time, buffer_shift_end_time)
							# if get_timedelta(log.punch_time) > buffer_shift_start_time and get_timedelta(log.punch_time) < buffer_shift_end_time:
							#     shift = g
							if log_type == "IN":
								if get_datetime(time) > buffer_shift_start_time and get_datetime(time) < buffer_shift_end_time:
									shift = g

							if log_type == "OUT":
								if get_datetime(time) > buffer_shift_start_time and get_datetime(time) < buffer_shift_end_time:
									shift = g

				## check shift from shift assignment 

				shift_assignments = frappe.db.sql("""
					SELECT 
						*
					FROM `tabShift Assignment`
					WHERE employee = %s
					and %s between start_date and end_date
					and docstatus=1
					ORDER BY start_date desc limit 1
				""", (log.employee_id, log.punch_date), as_dict=True)

				if shift_assignments:
					shift = shift_assignments[0].shift_type

				checkin = frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": log.employee_id,
					"log_type": log_type,
					"time": time,
					"device_id": log.terminal_id,
					"custom_area": log.area,
					"shift": shift
				})

				checkin.save()
				sql = f"UPDATE bio_attendance_log set is_processed = 'Y', message = '{checkin.name}' where name = '{log.name}'"
				frappe.db.sql(sql)

		except Exception as e:
			frappe.log_error('bio_attendance_exception', e)
			sql = f"UPDATE bio_attendance_log set is_processed = 'E', message = '{str(e)}' where name = '{log.name}'"
			frappe.db.sql(sql)


@frappe.whitelist()
def reset_attendance_log(bio_id):
	frappe.db.sql(
		f"""
		UPDATE
			bio_attendance_log
			set is_processed = 'N', message = null
		WHERE 
			name = '{bio_id}'
	""", as_dict=True)
	frappe.db.commit()

@frappe.whitelist()
def process_attendance_from_attendance_summary():
	yesterday = frappe.utils.add_to_date(frappe.utils.today(), days=-1)
	print(yesterday)

	result = []
	sql = frappe.db.sql(f"""
		SELECT
			e.name AS employee,
			e.employee_name,
			DATE(ec.time) AS date,
			MIN(CASE WHEN ec.log_type = 'IN' THEN TIME(ec.time) END) AS in_time,
			MAX(CASE WHEN ec.log_type = 'OUT' THEN TIME(ec.time) END) AS out_time,
			TIME(st.start_time) AS shift_start_time,
			TIME(st.end_time) AS shift_end_time,
			e.default_shift AS shift
		FROM
			`tabEmployee` AS e
		LEFT JOIN
			`tabEmployee Checkin` AS ec ON e.name = ec.employee
		LEFT JOIN
			`tabShift Type` AS st ON st.name = ec.shift
		LEFT JOIN
			`tabShift Assignment` AS sa ON sa.employee = e.name
		WHERE
			1=1
			AND DATE(ec.time) BETWEEN '{yesterday}' AND '{yesterday}'
		GROUP BY
			e.name, DATE(ec.time)
		ORDER BY
			date ASC
	""", as_dict=True)
	
	full_day = frappe.utils.get_time("08:00:00")
	half_day = frappe.utils.get_time("04:00:00")
	fifteen_minutes = frappe.utils.get_time("00:15:00")
	consecutive_late_entries = {}
	
	if sql:
		for data in sql:
			shift_sql = frappe.db.sql(f"""
				SELECT
					*
				FROM
					`tabShift Assignment` sa
				WHERE
					start_date BETWEEN '{yesterday}' AND '{yesterday}'
					AND employee = '{data["employee"]}'
			""", as_dict=True)
			
			
			if shift_sql:
				for shift in shift_sql:
					str_d = data["date"]
					d = frappe.utils.getdate(str_d)
					if shift["start_date"] == d:
						#frappe.log_error("shift['name']", shift['name'])
						data["shift"] = shift["shift_type"]
						
						
			if data["in_time"] is None and data["out_time"]:
				data["attendance"] = "Missing In"

			elif data["out_time"] is None and data["in_time"]:
				data["attendance"] = "Missing Out"

			elif frappe.utils.get_time(data["out_time"]) < frappe.utils.get_time(data["in_time"]):
				data["attendance"] = "Invalid Punch"

			elif data["out_time"] > data["in_time"]:
				hours = data["out_time"] - data["in_time"]
				data["worked_hours"] = hours
				#frappe.log_error('datetime_value', {'employee': data["employee"], 'full_day': full_day, 'hours': hours})
				if frappe.utils.get_time(hours) >= full_day:
					data["attendance"] = "Present"
				elif full_day >= frappe.utils.get_time(hours) >= half_day:
					data["attendance"] = "Half Day"
				else:
					data["attendance"] = "Absent"
			
				
			
			if data["shift_start_time"] and data["in_time"]:
				late_entry_difference = data["in_time"] - data["shift_start_time"]
				late_entry_difference_seconds = late_entry_difference.total_seconds()
				f_seconds = fifteen_minutes.hour * 3600 + fifteen_minutes.minute * 60 + fifteen_minutes.second
				if late_entry_difference_seconds > f_seconds :
					data["late_entry"] = "Yes"
					employee_name = data["employee_name"]
				
					consecutive_late_entries[employee_name] = consecutive_late_entries.get(employee_name, 0) + 1
		
					if consecutive_late_entries[employee_name] > 3:
						data["attendance"] = "Half Day"
				else:
					data["late_entry"] = "No"
					consecutive_late_entries[data["employee_name"]] = 0
			
			if data["shift_end_time"] and data["out_time"]:
				early_exit_difference = data["shift_end_time"] - data["out_time"]
				early_exit_difference_seconds = early_exit_difference.total_seconds()
				f_seconds = fifteen_minutes.hour * 3600 + fifteen_minutes.minute * 60 + fifteen_minutes.second
				if early_exit_difference_seconds > f_seconds :
					data["early_exit"] = "Yes"
				else:
					data["early_exit"] = "No"
					
			result.append(data)
	
	for r in result:
		if r.attendance in ('Absent', 'Present', 'Half Day'):
			attendance = frappe.new_doc("Attendance")
			attendance.update(
				{
					"doctype": "Attendance",
					"employee": r.employee,
					"attendance_date": yesterday,
					"status": r.attendance,
					"working_hours": r.worked_hours,
					"shift": r.shift,
					"late_entry": 1 if r.late_entry == 'Yes' else 0,
					"early_exit": 1 if r.early_exit == 'Yes' else 0,
					# "in_time": str(r.in_time),
					# "out_time": str(r.out_time),
				}
			).submit()

			checkins = frappe.db.get_all("Employee Checkin", filters=[["Employee Checkin","employee","=",r.employee],["Employee Checkin","time","Between",[yesterday,yesterday]]])
			for c in checkins:
				print(c.name)
				frappe.db.set_value("Employee Checkin", c.name, "attendance", attendance.name)



def process_attendance_from_no_check_in_applicable_grade():
	employees = frappe.db.sql("""
		SELECT 
			e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company
		FROM tabEmployee e
		LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
		LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
		WHERE g.custom_no_punch_applicable = 1
		AND e.status = 'Active'
	""", as_dict=True)

	if employees:
		for e in employees:
			count = frappe.db.count("Attendance", filters={"employee": e.name, "attendance_date": frappe.utils.nowdate(), "docstatus": 1})
			if count == 0:
				attendance = frappe.get_doc({
					"naming_series": "HR-ATT-.YYYY.-",
					"doctype": "Attendance",
					"employee": e.name,
					"status": "Present",
					"attendance_date": frappe.utils.nowdate(),
					"company": e.company,
				})

				attendance.save()
				attendance.add_tag("No Check in Required")
				attendance.submit()



def process_attendance_from_single_check_in_applicable_grade():
	employees = frappe.db.sql("""
		SELECT 
			e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company
		FROM tabEmployee e
		LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
		LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
		WHERE g.custom_no_punch_applicable = 1
		AND e.status = 'Active'
	""", as_dict=True)

	if employees:
		for e in employees:
			count = frappe.db.count("Attendance", filters={"employee": e.name, "attendance_date": frappe.utils.nowdate(), "docstatus": 1})
			if count == 0:
				attendance = frappe.get_doc({
					"naming_series": "HR-ATT-.YYYY.-",
					"doctype": "Attendance",
					"employee": e.name,
					"status": "Present",
					"attendance_date": frappe.utils.nowdate(),
					"company": e.company,
				})

				attendance.save()
				attendance.add_tag("No Check in Required")
				attendance.submit()

