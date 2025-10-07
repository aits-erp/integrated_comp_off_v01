from frappe.core.doctype.user.user import User


class UserOverride(User):
    def autoname(self):
        """set name as Email Address"""
        if self.get("is_admin") or self.get("is_guest"):
            self.name = self.first_name
        else:
            self.email = self.email.strip().lower()
            self.name = self.username

    def validate_email_type(self, email):
        # By default, document name is considered as email, which will break if name is not email.
        # So we explicitly pass email field to validate_email_type method.
        email = self.get("email") or email
        super().validate_email_type(email)
