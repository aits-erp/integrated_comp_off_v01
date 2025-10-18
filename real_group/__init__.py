__version__ = "0.0.1"


def monkey_patch():
    from frappe.www import login

    from real_group.api.overrides.auth import send_login_link as custom_send_login_link

    login.send_login_link = custom_send_login_link

    import hrms.hr.doctype.employee_checkin.employee_checkin as ec

    from real_group.overrides.employee_checkin import mark_attendance_and_link_log

    ec.mark_attendance_and_link_log = mark_attendance_and_link_log


monkey_patch()  # nosemgrep
