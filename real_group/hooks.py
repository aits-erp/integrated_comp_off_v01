app_name = "real_group"
app_title = "Real Group"
app_publisher = "Step Tech"
app_description = "Custom Developments for Real Group"
app_email = "admin@step-tech.in"
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
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
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
jinja = {
	"methods": ["real_group.real_group.utils.get_qr_code", "real_group.real_group.utils.employee_advance_details"]
}

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
	"User": "real_group.overrides.CustomUser",
    "Employee": "real_group.overrides.CustomEmployee",
    "Employee Checkin": "real_group.overrides.CustomEmployeeCheckin",
    "Compensatory Leave Request": "real_group.overrides.CustomCompensatoryLeaveRequest",
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
        "after_insert": ["real_group.real_group.integration.create_employee"],
        "on_update": ["real_group.real_group.integration.update_employee"]
    },

    "User": {
        "after_insert": ["real_group.real_group.integration.create_user"],
        "on_update": ["real_group.real_group.integration.update_user"],
        "update_password": ["real_group.real_group.integration.update_user_password"]
    },

    # "Salary Structure Assignment": {
    #     "before_save": ["real_group.real_group.arrears.process_arrear"]
    # },

    "Salary Slip": {
        "on_submit": ["real_group.real_group.integration.create_salary_slip"],
        "on_cancel": ["real_group.real_group.integration.cancel_salary_slip"],
    #    "before_save": ["real_group.real_group.arrears.arrears_in_current_sal_slip"]
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "real_group.real_group.attendance.process_attendance_log"
        ],
        # "* * * * *": [
        #     "real_group.real_group.attendance.pull_data_from_postgre"
        # ],
        "0 23 * * *": [
            "real_group.real_group.attendance.process_attendance_from_attendance_summary"
        ],
        "0 9 * * *": [
            "real_group.real_group.attendance.process_attendance_from_no_check_in_applicable_grade",
            "real_group.real_group.notifications.send_birthday_wishes"
        ],
        "59 23 * * *": [
            "real_group.real_group.attendance.process_attendance_from_single_check_in_applicable_grade"
        ],
        "01 0 * * *": [
            "real_group.real_group.attendance.terminate_leave_allocation_on_expiry"
        ]    
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
	# "frappe.desk.doctype.event.event.get_events": "real_group.event.get_events",
    "frappe.core.doctype.user.user.update_password": "real_group.real_group.integration.update_user_password"
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
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }



from frappe.www import login
from real_group.overrides import send_login_link as custom_send_login_link
login.send_login_link = custom_send_login_link

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Real Group"]]},
    # {"dt": "Report", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Print Format", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Server Script", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Client Script", "filters": [["module", "=", "Real Group"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Real Group"]]},
    # {"dt": "Workflow"},
    # {"dt": "Workflow State"},
    # {"dt": "Workflow Action Master"},
    {"dt": "Web Form", "filters": [["module", "=", "Real Group"]]}
]


