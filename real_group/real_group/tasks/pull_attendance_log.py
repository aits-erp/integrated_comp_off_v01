import frappe
import psycopg
from frappe import _SingleDocument


def pull_data_from_postgre():
    settings: _SingleDocument = frappe.get_doc("Real Group Settings")

    if not settings.time_pro_database or not settings.time_pro_password:
        return

    conninfo = (
        f"dbname={settings.time_pro_database} "
        f"user={settings.time_pro_user} "
        f"password={settings.get_password('time_pro_password')} "
        f"host={settings.time_pro_host} "
        f"port={settings.time_pro_port}"
    )

    with psycopg.connect(conninfo, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'Asia/Kolkata'")
            cur.execute(
                """
                SELECT
                     tr.id time_pro_reference_id,
                     tr.punch_time,
                     tr.emp_code employee_id,
                     tr.punch_time::date punch_date,
                     tr.punch_time::time punch_time1,
                     tr.area_alias area,
                     (SELECT punch_direction FROM iclock_terminal t WHERE t.id = tr.terminal_id) punch_direction,
                     tr.punch_state terminal_id,
                     'N' is_processed,
                     tr.upload_time
                FROM iclock_transaction tr
                WHERE tr.upload_time > %s
                ORDER BY tr.upload_time ASC
                LIMIT 1000
            """,
                (settings.time_pro_last_sync_on,),
            )

            rows = cur.fetchall()
            result = [dict((cur.description[i][0], val) for i, val in enumerate(row)) for row in rows]

    # Insert into frappe db
    for r in result:
        frappe.db.sql(
            """
            INSERT INTO bio_attendance_log
                (employee_id, punch_date, punch_time, area, punch_direction, terminal_id, is_processed, time_pro_reference_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                r.get("employee_id"),
                r.get("punch_date"),
                str(r.get("punch_time1")),
                r.get("area"),
                r.get("punch_direction"),
                r.get("terminal_id"),
                r.get("is_processed"),
                r.get("time_pro_reference_id"),
            ),
        )

        upload_time = r.get("upload_time").strftime("%Y-%m-%d %H:%M:%S.%f")
        frappe.db.set_value("Real Group Settings", "Real Group Settings", "time_pro_last_sync_on", str(upload_time))

    frappe.db.commit()
