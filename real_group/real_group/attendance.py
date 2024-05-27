import frappe

@frappe.whitelist()
def process_attendance_log():
    attendance_logs = frappe.db.sql(
        """
        SELECT 
            *
        FROM
            bio_attendance_log
        WHERE is_processed = 'N'
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


                shift = frappe.db.get_value("Employee", log.employee_id, "default_shift") 

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