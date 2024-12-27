import frappe
from frappe.utils import get_timedelta, get_datetime, add_to_date
import psycopg2
from operator import itemgetter
from frappe.model.document import Document
import calendar
from datetime import datetime
from itertools import groupby
from hrms.hr.doctype.leave_application.leave_application import get_approved_leaves_for_period, get_leave_balance_on


def pull_data_from_postgre():

	settings = frappe.get_doc("Real Group Settings")
	conn = psycopg2.connect(database = settings.time_pro_database, 
                        user = settings.time_pro_user, 
                        host= settings.time_pro_host,
                        password = settings.get_password("time_pro_password"),
                        port = settings.time_pro_port)
	
	cur = conn.cursor()
	cur.execute("SET TIME ZONE 'Asia/Kolkata'")
	cur.execute(f"""
		SELECT
			 tr.id time_pro_reference_id, 
			 tr.punch_time,
			 tr.emp_code employee_id,
			 tr.punch_time::date punch_date,
			 tr.punch_time::time punch_time1,
			 tr.area_alias area,
			 (SELECT punch_direction FROM iclock_terminal t where t.id = tr.terminal_id) punch_direction,
			 tr.punch_state terminal_id,
			 'N' is_processed,
			 tr.upload_time
		FROM
			iclock_transaction tr
		WHERE
			 tr.upload_time > '{settings.time_pro_last_sync_on}'
		ORDER BY tr.upload_time asc
		LIMIT 500
	""")

	rows = cur.fetchall()
	conn.commit()
	conn.close()

	result = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in rows]

	for r in result:
		# print(r)
		# print(str(r.get("punch_time1")), type(r.get("punch_time1")))
		# print(r.get("upload_time").strftime('%Y-%m-%d %H:%M:%S.%f'), type(r.get("upload_time")))
		upload_time = r.get("upload_time").strftime('%Y-%m-%d %H:%M:%S.%f')
		frappe.db.sql(f"""
			INSERT INTO bio_attendance_log
				(employee_id, punch_date, punch_time, area, punch_direction, terminal_id, is_processed, time_pro_reference_id)
				VALUES
				(
					'{r.get("employee_id")}',
					'{r.get("punch_date")}',
					'{str(r.get("punch_time1"))}',
					'{r.get("area")}',
					'{r.get("punch_direction")}',
					'{r.get("terminal_id")}',
					'{r.get("is_processed")}',
					'{r.get("time_pro_reference_id")}'
				)
		""")
		frappe.db.set_value("Real Group Settings", "Real Group Settings", "time_pro_last_sync_on", str(upload_time))
		frappe.db.commit()

@frappe.whitelist()
def process_attendance_log():

	process_attendance_log_in()
	process_attendance_log_out()

def process_attendance_log_in():

	attendance_logs = frappe.db.sql(
		"""
		SELECT 
			*
		FROM
			bio_attendance_log
		WHERE is_processed = 'N'
		AND punch_direction = 'I'
		AND LENGTH(employee_id) >= 5
		ORDER by employee_id, punch_date, punch_time
		LIMIT 1000
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

				allowed_shifts = []
				# check shift from employee master

				shift = frappe.db.get_value("Employee", log.employee_id, "default_shift")
				allowed_shifts.append(shift)

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
					allowed_shifts.append(shift)


				## check shift from employee grade master
				employee_grade = frappe.db.get_value("Employee", log.employee_id, "grade")

				if employee_grade:

					grade = frappe.get_doc("Employee Grade", employee_grade)

					for shift in grade.custom_allowed_shifts:
						allowed_shifts.append(shift.shift)

					allowed_shifts_str = ','.join(f"'{s}'" for s in allowed_shifts)

					sql = f"""
						SELECT
							s.name,
							s.start_time,
							ABS(TIMEDIFF(s.start_time, '{log.punch_time}')) diff
						FROM `tabShift Type` s
						WHERE
							s.name IN ({allowed_shifts_str})
						ORDER BY
							diff, s.start_time
					"""
					grade_shift = frappe.db.sql(sql, as_dict=True)
					shift = grade_shift[0].name

				checkin = frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": log.employee_id,
					"log_type": log_type,
					"time": time,
					"device_id": log.terminal_id,
					"custom_area": log.area,
					"shift": shift,
					"custom_bio_log_id": log.name,
					"custom_is_temporary_shift": 1
				})

				checkin.save()
				sql = f"UPDATE bio_attendance_log set is_processed = 'Y', message = '{checkin.name}' where name = '{log.name}'"
				frappe.db.sql(sql)

		except Exception as e:
			frappe.log_error('bio_attendance_exception')
			sql = f"UPDATE bio_attendance_log set is_processed = 'E', message = '{str(e)}' where name = '{log.name}'"
			frappe.db.sql(sql)

def process_attendance_log_out():
	
	attendance_logs = frappe.db.sql(
		"""
		SELECT 
			*
		FROM
			bio_attendance_log
		WHERE is_processed = 'N'
		AND punch_direction = 'O'
		AND LENGTH(employee_id) >= 5
		ORDER by employee_id, punch_date, punch_time
		LIMIT 1000
	""", as_dict=True)

	for log in attendance_logs:
		
		try:

			if not frappe.db.exists("Employee", log.employee_id):
				sql = f"UPDATE bio_attendance_log set is_processed = 'E', message = 'Employee ID Does not exists' where name = '{log.name}'"
				frappe.db.sql(sql)
			else:
				log_type = ""
				time = f"{log.punch_date} {log.punch_time}"
				
				if log.punch_direction == "O":
					log_type = "OUT"

				# check shift from employee master

				allowed_shifts = []
				# check shift from employee master

				shift = frappe.db.get_value("Employee", log.employee_id, "default_shift")
				allowed_shifts.append(shift)

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
					allowed_shifts.append(shift)


				## check shift from employee grade master
				employee_grade = frappe.db.get_value("Employee", log.employee_id, "grade")

				if employee_grade:

					grade = frappe.get_doc("Employee Grade", employee_grade)

					for shift in grade.custom_allowed_shifts:
						allowed_shifts.append(shift.shift)

					allowed_shifts_str = ','.join(f"'{s}'" for s in allowed_shifts)

					sql = f"""
						SELECT
							s.name,
							s.start_time,
							ABS(TIMEDIFF(s.end_time, '{log.punch_time}')) diff
						FROM `tabShift Type` s
						WHERE
							s.name IN ({allowed_shifts_str})
						ORDER BY
							diff, s.start_time
					"""
					grade_shift = frappe.db.sql(sql, as_dict=True)
					shift = grade_shift[0].name


						# for g in grade_shifts:

							# shift_start_time, shift_end_time, cross_days = frappe.db.get_value("Shift Type", g, ["start_time", "end_time", "custom_end_across_days"])
							# shift_start_time = f"{log.punch_date} {str(shift_start_time)}"
							# shift_end_time = f"{add_to_date(log.punch_date, days=cross_days)} {str(shift_end_time)}"
							# buffer_shift_start_time = get_datetime(shift_start_time) - get_timedelta("00:30:00")
							# buffer_shift_end_time = get_datetime(shift_end_time) - get_timedelta("00:30:00")

							# if log_type == "IN":
							# 	if get_datetime(time) > buffer_shift_start_time and get_datetime(time) < buffer_shift_end_time:
							# 		shift = g

							# if log_type == "OUT":
							# 	if get_datetime(time) > buffer_shift_start_time and get_datetime(time) < buffer_shift_end_time:
							# 		shift = g



				## apply shift based on check out time to the checkins done

				shift_start_time = str(frappe.db.get_value("Shift Type", shift, "start_time"))
				checkins = frappe.db.sql("""
					SELECT 
						*
					FROM `tabEmployee Checkin`
					WHERE employee = %s
					AND time between %s and %s
					AND custom_is_temporary_shift = 1
					AND log_type = 'IN'
				""", (log.employee_id, f"{log.punch_date} 00:00:00", f"{log.punch_date} {log.punch_time}"), as_dict=True)

				for c in checkins:
					frappe.db.set_value("Employee Checkin", c.name, "shift", shift)
					frappe.db.set_value("Employee Checkin", c.name, "custom_is_temporary_shift", 0)

				#update shift in check out type 

				# frappe.log_error("doc.time", doc.time)
				custom_cross_days = 0
				if log_type == "OUT":
					start = frappe.utils.get_time("03:00:00")
					end = frappe.utils.get_time("12:00:00")
					
					x = time.split(" ")
					if start <= frappe.utils.get_time(x[1]) <= end:
						custom_cross_days = 1

				checkin = frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": log.employee_id,
					"log_type": log_type,
					"time": time,
					"device_id": log.terminal_id,
					"custom_area": log.area,
					"shift": shift,
					"custom_bio_log_id": log.name,
					"custom_cross_days": custom_cross_days
				})

				checkin.save()
				sql = f"UPDATE bio_attendance_log set is_processed = 'Y', message = '{checkin.name}' where name = '{log.name}'"
				frappe.db.sql(sql)

		except Exception as e:
			frappe.log_error('bio_attendance_exception')
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

	bio = frappe.db.sql("SELECT * from bio_attendance_log where name = %s", bio_id)
	if bio:
		check_ins = frappe.db.get_all("Employee Checkin", filters={"custom_bio_log_id":  bio_id})
		for check_in in check_ins:
			frappe.delete_doc("Employee Checkin", check_in.get("name"))

	frappe.db.commit()

@frappe.whitelist()
@frappe.whitelist()
def process_attendance_from_attendance_summary():

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
	""",as_dict=1)

	for emp in all_employee:
		frappe.enqueue("real_group.real_group.attendance.process_attendance_from_attendance_summary_queue", queue="long", timeout=3600, employee=emp.name, company=emp.company)

def process_attendance_from_attendance_summary_queue(employee, company):

	# employee_list = frappe.db.sql(f"""
	# 	SELECT
	# 		DISTINCT e.name,
	# 		e.employee_name,
	# 		e.company,
	# 		e.branch
	# 	FROM
	# 		`tabEmployee` e
	# 	LEFT JOIN
	# 		`tabEmployee Grade` eg on eg.name = e.grade
	# 	WHERE
	# 		e.status = 'Active'
	# 		AND eg.custom_single_punch_applicable = 0
	# 		AND eg.custom_no_punch_applicable = 0
	# 		-- AND name = '50003'
	# 	GROUP BY 
	#         e.name
	# 	LIMIT 600
	# 	""", as_dict=True)

	# employee_list = [{"name": "50003", "employee_name": "OMPRAKASH", "company": "API Ispat and Powertech Private Limited", "branch": "Plant"},
	# {"name": "50004", "employee_name": "DIWAKAR", "company": "API Ispat and Powertech Private Limited", "branch": "Plant"}]

	attendance_for_date = frappe.utils.getdate()
	year = str(attendance_for_date.year)
	month = attendance_for_date.strftime("%b")	
	month_number = datetime.strptime(month, "%b").month

	fr_date = datetime(int(year), month_number, 1).date()
	t_date = frappe.utils.getdate()
	x = frappe.call(
		"frappe.desk.query_report.run",
		report_name="Biometric Attendance Summary To Mark Attendance",
		filters={
			"company": company,
			"branch": "",
			"month": month,
			"year": year,
			"employee": employee
		},
		ignore_prepared_report=True
	)
	filtered_result = []
	
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
			AND e.name = %s
	""", employee, as_dict=1)

	all_emp_list = {emp["name"] for emp in all_employee}

	emp_filter = set()

	for i in x.get("result"):
		employee_code = i.get("employee")
		if employee_code in all_emp_list and employee_code not in emp_filter:
			emp_filter.add(employee_code)
		i["attendance_date"] = str(i.get("date"))
		if i["in_time"] is None and i["out_time"] is None:
			continue
		elif i.get("attendance") == "Missing In and Out" or i.get("attendance") == "Not Present":
			continue
		elif i.get("attendance") == "" or i.get("attendance") is None:
			continue
		else:
			filtered_result.append(i)

	filtered_result.sort(key=itemgetter('employee'))

	for key, group in groupby(filtered_result, key=itemgetter('employee')):
		grouped = {}
		
		# Iterate over the current group of items for this employee
		for item in group:
			date = item.get("attendance_date")
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

		# Merge missing dates with filtered result for the current employee
		merged_dict = {item["attendance_date"]: item for item in missing_dates + inner_filtered_result}

		merged_list = list(merged_dict.values())
		# frappe.log_error("merged_list", merged_list)

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

			
			if r.get("attendance") == 'POH' or r.get("attendance") == 'POW':
				mark_attendance = 'Present'
			elif r.get("attendance") is None or r.get('attendance') == '':
				mark_attendance = 'Absent'
			else:	
				mark_attendance = r.get("attendance")
				#attendance_tag = "l"
				#frappe.log_error("reprocess_attendance", {"attendance": r.get("attendance"), "mark_attendance": mark_attendance, "r": r})
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

			attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": r.get("employee"), "attendance_date": r.get("attendance_date"), "docstatus": "1"})
			# for a in attendance_exists:
			# 	att = frappe.get_doc("Attendance", a.get("name"))
			# 	att.cancel()
			# 	att.delete()
			
			if not attendance_exists:
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
							"early_exit": 1 if r.get("early_exit") == 'Yes' else 0
						}
					).save()
					attendance.submit()
	# cur_date = fr_date
	# for empl in emp_filter:
		
	# 	while cur_date <= t_date:
	# 		attendance_exists = frappe.db.get_all("Attendance", fields=["name"], filters={"employee": empl, "attendance_date": cur_date, "docstatus": "1"})
	# 		# for a in attendance_exists:
	# 		# 	att = frappe.get_doc("Attendance", a.get("name"))
	# 		# 	att.cancel()
	# 		# 	att.delete()
	# 		if not attendance_exists:
	# 			attendance = frappe.new_doc("Attendance")
	# 			attendance.update(
	# 				{
	# 					"doctype": "Attendance",
	# 					"employee": empl,
	# 					"attendance_date": cur_date,
	# 					"status": "Absent",
	# 					"custom_attendance_tag": "No Punch Data",
	# 					# "custom_half_type": half_type,
	# 					# "custom_reason": r.get("attendance"),
	# 					# "shift": r.get("shift"),
	# 					# "late_entry": 1 if r.get("late_entry") == 'Yes' else 0,
	# 					# "early_exit": 1 if r.get("early_exit") == 'Yes' else 0,
	# 					# "custom_reprocess_reference": self.name
	# 				}
	# 			).save()
	# 			attendance.submit()
	# 		frappe.utils.add_to_date(cur_date, days=1)

def process_attendance_from_no_check_in_applicable_grade():
	employees = frappe.db.sql("""
		SELECT 
			e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company, e.holiday_list
		FROM tabEmployee e
		LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
		LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
		WHERE g.custom_no_punch_applicable = 1
		AND e.status = 'Active'
	""", as_dict=True)

	if employees:
		for e in employees:
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
                    hl.name = '{e["holiday_list"]}'
                    AND h.holiday_date = '{frappe.utils.today()}'
                GROUP BY
                    h.holiday_date
            """, as_dict = True)
			if len(holiday_sql) == 0:
				
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
			e.name, e.default_shift, s.start_time, s.end_time, e.grade, e.company, e.holiday_list
		FROM tabEmployee e
		LEFT JOIN `tabEmployee Grade` g ON e.grade = g.name
		LEFT JOIN `tabShift Type` s ON s.name = e.default_shift
		WHERE g.custom_single_punch_applicable = 1
		AND e.status = 'Active'
	""", as_dict=True)

	if employees:
		st = frappe.utils.nowdate() + " " + "00:00:00"
		et = frappe.utils.nowdate() + " " + "23:59:59"
		for e in employees:
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
			""", (e.name, st, et), as_dict = True)
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
						hl.name = '{e["holiday_list"]}'
						AND h.holiday_date = '{frappe.utils.today()}'
					GROUP BY
						h.holiday_date
				""", as_dict = True)
				if len(holiday_sql) == 0:
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
						attendance.add_tag("Single Check in Required")
						attendance.submit()

def terminate_leave_allocation_on_expiry():
	today = frappe.utils.add_to_date(frappe.utils.getdate(), days=0)
	comp_lv_req = frappe.db.get_all("Compensatory Leave Request", filters={"expiry": today, "docstatus": 1})
	print(comp_lv_req)
	if comp_lv_req:
		for count in comp_lv_req:
			comp_leave = frappe.get_doc("Compensatory Leave Request", count.get("name"))
			allocated_leave_list = frappe.db.get_all("Leave Allocation", filters={"leave_type": "Compensatory Off", "employee": comp_leave.employee})
			if allocated_leave_list:
				al = frappe.get_doc("Leave Allocation", allocated_leave_list[0].get("name"))
				leave_balance = get_leave_balance_on(
					comp_leave.employee,
					comp_leave.leave_type,
					frappe.utils.getdate(),
					frappe.utils.getdate(),
					consider_all_leaves_in_the_allocation_period=True,
					for_consumption=True,
				)
				difference = al.new_leaves_allocated - comp_leave.credit
				if difference >= (leave_balance.get("leave_balance") - comp_leave.credit):		
					al.new_leaves_allocated = al.new_leaves_allocated - comp_leave.credit
					al.total_leaves_allocated = al.total_leaves_allocated - comp_leave.credit
					al.save()
					frappe.db.set_value("Compensatory Leave Request", comp_leave.name, "custom_is_expired", 1)