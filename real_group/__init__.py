__version__ = "0.0.1"


def monkey_patch():
    from frappe.www import login

    from real_group.api.overrides.auth import send_login_link as custom_send_login_link

    login.send_login_link = custom_send_login_link

    import hrms.hr.doctype.employee_checkin.employee_checkin as ec

    from real_group.overrides.employee_checkin import mark_attendance_and_link_log

    ec.mark_attendance_and_link_log = mark_attendance_and_link_log

    import hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment as lpa

    from real_group.overrides.leave_policy_assignment import get_earned_leaves, get_leave_type_details

    lpa.get_leave_type_details = get_leave_type_details

    import hrms.hr.utils as hr_utils

    hr_utils.get_earned_leaves = get_earned_leaves


monkey_patch()  # nosemgrep
