__version__ = "0.0.1"


def monkey_patch():
    from frappe.www import login

    from real_group.overrides import send_login_link as custom_send_login_link

    login.send_login_link = custom_send_login_link


monkey_patch()
