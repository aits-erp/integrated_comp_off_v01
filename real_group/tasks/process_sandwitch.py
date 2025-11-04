import frappe
from frappe.utils import date_diff, get_first_day, getdate

from real_group.utils import is_holiday_for_employee


def process():
    """Daily job to find holidays sandwiched between absences or leaves (from month start to today) and mark them as Absent"""
    today = getdate()
    month_start = get_first_day(today)

    grades = frappe.get_all("Employee Grade", filters={"custom_sandwich_flag": 1}, pluck="name")
    employees = frappe.get_all("Employee", filters={"status": "Active", "grade": ["in", grades]}, pluck="name")

    for emp in employees:
        records = frappe.get_all(
            "Attendance",
            filters={
                "employee": emp,
                "attendance_date": ["between", [month_start, today]],
            },
            fields=["attendance_date", "status", "name"],
            order_by="attendance_date asc",
        )

        if not records:
            continue

        records.sort(key=lambda x: x.attendance_date)
        dates = [r.attendance_date for r in records]
        statuses = {r.attendance_date: r.status for r in records}

        for i in range(1, len(dates) - 1):
            curr = dates[i]
            prev = dates[i - 1]
            nxt = dates[i + 1]

            # Skip if already absent
            if statuses.get(curr) == "Absent":
                continue

            # Skip if not a holiday
            holiday_info = is_holiday_for_employee(emp, curr)
            if not holiday_info.get("is_holiday"):
                continue

            # Check if both adjacent days are consecutive and absent/leave
            if date_diff(curr, prev) == 1 and date_diff(nxt, curr) == 1:
                if statuses.get(prev) in ("Absent", "On Leave") and statuses.get(nxt) in ("Absent", "On Leave"):
                    # Cancel and mark absent (same logic)

                    frappe.logger().info(
                        f"[Sandwich Job] {emp}: {curr} marked as Absent (sandwiched between {prev} & {nxt})"
                    )

                    old_attendance = frappe.db.exists("Attendance", {"employee": emp, "attendance_date": curr})
                    if old_attendance:
                        # Cancel existing attendance with a comment
                        old_doc = frappe.get_doc("Attendance", old_attendance)
                        if old_doc.docstatus == 1:
                            old_doc.add_comment(
                                "Comment",
                                f"Auto-cancelled by sandwich job: converted holiday {curr} to Absent",
                            )
                            old_doc.cancel()

                    # Create new Absent attendance
                    new_attendance = frappe.get_doc(
                        {
                            "doctype": "Attendance",
                            "employee": emp,
                            "attendance_date": curr,
                            "status": "Absent",
                            "custom_attendance_tag": "A",
                        }
                    )
                    new_attendance.insert(ignore_permissions=True)
                    new_attendance.submit()

    frappe.db.commit()
