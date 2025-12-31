// Copyright (c) 2024, Step Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reprocess Attendance", {
  employee: function (frm) {
    frappe.db.get_value("Employee", frm.doc.employee, ["company", "branch"]).then((r) => {
      const data = r.message;
      frm.set_value("company", data.company);
      frm.set_value("branch", data.branch);
    });
  },
  validate(frm) {
    frm.trigger("validateDate");
  },
  to_date(frm) {
    frm.trigger("validateDate");
  },
  validateDate(frm) {
    const dayDiff = Math.abs(parseInt(frappe.datetime.get_day_diff(frm.doc.to_date, frappe.datetime.get_today())));
    if (dayDiff < 3) {
      frappe.msgprint(__("To Date must be at least 2 days before today's date"));
      frappe.validated = false;
    }
  },
});
