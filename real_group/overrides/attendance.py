import frappe
from frappe import _
from frappe.utils import get_link_to_form
from hrms.hr.doctype.attendance.attendance import Attendance


class AttendanceOverride(Attendance):
    def on_cancel(self):
        self.unlink_attendance_from_checkins_override()

    def unlink_attendance_from_checkins_override(self):
        if frappe.flags.in_reprocess_attendance:
            return
        EmployeeCheckin = frappe.qb.DocType("Employee Checkin")
        linked_logs = (
            frappe.qb.from_(EmployeeCheckin)
            .select(EmployeeCheckin.name)
            .where(EmployeeCheckin.attendance == self.name)
            .run(as_dict=True)
        )
        if linked_logs:
            (
                frappe.qb.update(EmployeeCheckin).set("attendance", "").where(EmployeeCheckin.attendance == self.name)
            ).run()
            frappe.msgprint(
                msg=_("Unlinked Attendance record from Employee Checkins: {}").format(
                    ", ".join(get_link_to_form("Employee Checkin", log.name) for log in linked_logs)
                ),
                title=_("Unlinked logs"),
                indicator="blue",
                is_minimizable=True,
                wide=True,
            )
