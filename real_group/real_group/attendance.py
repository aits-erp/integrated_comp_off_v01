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
            frappe.log_error(e)
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