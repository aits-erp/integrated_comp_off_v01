app_name = "real_group"
app_title = "Real Group"
app_publisher = "rtCamp"
app_description = "Custom Developments for Real Group"
app_email = "frappe@rtcamp.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/real_group/css/real_group.css"
# app_include_js = "/assets/real_group/js/real_group.js"

# include js, css files in header of web template
# web_include_css = "/assets/real_group/css/real_group.css"
# web_include_js = "/assets/real_group/js/real_group.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "real_group/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "User": "public/js/form/user.js",
    "Leave Application": "public/js/form/leave_application.js",
    "Employee": "public/js/form/employee.js",
    "Company": "public/js/form/company.js",
    "Employee Performance Feedback": "public/js/form/employee_performance_feedback.js",
    "Appraisal Template": "public/js/form/appraisal_template.js",
    "Employee Advance": "public/js/form/employee_advance.js",
    "Employee Grade": "public/js/form/employee_grade.js",
    "Attendance Request": "public/js/form/attendance_request.js",
    "Salary Structure": "public/js/form/salary_structure.js",
    "Interview": "public/js/form/interview.js",
    "Compensation Matrix": "public/js/form/compensation_matrix.js",
    "Arrear Slip": "public/js/form/arrear_slip.js",
    "Medical History": "public/js/form/medical_history.js",
    "Employee Onboarding Form": "public/js/form/employee_onboarding_form.js",
    "Additional Salary": "public/js/form/additional_salary.js",
    "Expense Claim": "public/js/form/expense_claim.js",
    "Skip Loan Installment": "public/js/form/skip_loan_installment.js",
    "Reprocess Attendance": "public/js/form/reprocess_attendance.js",
    "Appointment Letter": "public/js/form/appointment_letter.js",
    "Real Group User": "public/js/form/real_group_user.js",  # TODO: Check if this is required
    "Salary Slip": "public/js/form/salary_slip.js",
}
doctype_list_js = {
    "Leave Application": "public/js/list/leave_application.js",
    "Attendance": "public/js/list/attendance.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "real_group/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {"methods": ["real_group.real_group.utils.get_qr_code", "real_group.real_group.utils.employee_advance_details"]}

# Installation
# ------------

# before_install = "real_group.install.before_install"
# after_install = "real_group.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "real_group.uninstall.before_uninstall"
# after_uninstall = "real_group.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "real_group.utils.before_app_install"
# after_app_install = "real_group.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "real_group.utils.before_app_uninstall"
# after_app_uninstall = "real_group.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "real_group.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "User": "real_group.overrides.user.UserOverride",
    "Employee Checkin": "real_group.overrides.employee_checkin.EmployeeCheckinOverride",
    "Compensatory Leave Request": "real_group.overrides.compensatory_leave_request.CompensatoryLeaveRequestOverride",
    # "Leave Application": "real_group.overrides.CustomLeaveApplication", # Need not do override
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Employee": {
        "autoname": "real_group.doc_events.employee.autoname",
        "after_insert": ["real_group.real_group.integration.create_employee"],
        "on_update": ["real_group.real_group.integration.update_employee"],
    },
    "Employee Checkin": {
        "validate": ["real_group.doc_events.employee_checkin.validate"],
        "after_insert": [
            "real_group.doc_events.employee_checkin.after_insert",
        ],
        "before_insert": [
            "real_group.doc_events.employee_checkin.before_insert",
        ],
    },
    "Attendance Request": {
        "validate": ["real_group.doc_events.attendace_request.validate"],
        "before_cancel": ["real_group.doc_events.attendace_request.before_cancel"],
        "before_delete": ["real_group.doc_events.attendace_request.before_delete"],
        "before_insert": ["real_group.doc_events.attendace_request.before_insert"],
    },
    "User": {
        "after_insert": ["real_group.real_group.integration.create_user"],
        "on_update": ["real_group.real_group.integration.update_user"],
        "update_password": ["real_group.real_group.integration.update_user_password"],
    },
    "Salary Structure Assignment": {
        "before_save": [
            # "real_group.real_group.arrears.process_arrear",
        ],
        "before_submit": ["real_group.real_group.integration.insert_salary_structure"],
    },
    "Salary Slip": {
        "on_submit": ["real_group.real_group.integration.create_salary_slip"],
        "on_cancel": ["real_group.real_group.integration.cancel_salary_slip"],
        #    "before_save": ["real_group.real_group.arrears.arrears_in_current_sal_slip"]
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "*/2 * * * *": ["real_group.tasks.process_employee_checkin.process"],
        # TODO: This will be removed, since not being used.
        # "* * * * *": ["real_group.tasks.pull_attendance_log.pull_data_from_postgre"],
        "0 1 * * *": ["real_group.tasks.process_attendance.process"],
        "1 00 * * *": ["real_group.real_group.attendance.process_attendance_from_attendance_summary"],
        "0 9 * * *": [
            "real_group.tasks.process_attendance_for_no_checkin_applicable.process",
            "real_group.real_group.notifications.send_birthday_wishes",
        ],
        "0 3 * * *": ["real_group.tasks.process_attendance.process"],
        "59 23 * * *": ["real_group.tasks.process_attendance_for_single_checkin.process"],
        # "01 0 * * *": [
        #     "real_group.real_group.attendance.terminate_leave_allocation_on_expiry"
        # ],
        "0 13 * * *": ["real_group.tasks.c_off_allocation.process"],
        "5 0 2 * *": ["real_group.real_group.attendance.process_attendance_for_last_day_of_month"],
    }
}

# scheduler_events = {
# 	"all": [
# 		"real_group.tasks.all"
# 	],
# 	"daily": [
# 		"real_group.tasks.daily"
# 	],
# 	"hourly": [
# 		"real_group.tasks.hourly"
# 	],
# 	"weekly": [
# 		"real_group.tasks.weekly"
# 	],
# 	"monthly": [
# 		"real_group.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "real_group.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.update_password": "real_group.api.overrides.user.update_user_password",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "real_group.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["real_group.utils.before_request"]
# after_request = ["real_group.utils.after_request"]

# Job Events
# ----------
# before_job = ["real_group.utils.before_job"]
# after_job = ["real_group.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"real_group.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Report", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Print Format", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Server Script", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Real Group"]]},
]
