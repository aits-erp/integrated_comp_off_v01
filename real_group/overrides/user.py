from frappe.core.doctype.user.user import User


class UserOverride(User):
    def autoname(self):
        """set name as Email Address"""
        if self.get("is_admin") or self.get("is_guest"):
            self.name = self.first_name
        else:
            self.email = self.email.strip().lower() if self.email else ""
            self.name = self.username

    def validate_email_type(self, email):
        # No need to validate email, since it is not used.
        pass
