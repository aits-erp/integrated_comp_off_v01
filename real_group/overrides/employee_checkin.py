from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin


class EmployeeCheckinOverride(EmployeeCheckin):
    def fetch_shift(self):
        if hasattr(self, "flags") and not getattr(self.flags, "is_shift_fetch_required", False):
            return
        super().fetch_shift()
