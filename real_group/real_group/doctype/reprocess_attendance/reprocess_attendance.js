// Copyright (c) 2024, Step Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Reprocess Attendance", {
  refresh(frm) {
    if (frm.doc.reprocess_attendance_bulk) {
      frm.set_df_property("company", "read_only", 1);
      frm.set_df_property("branch", "read_only", 1);
      frm.set_df_property("division", "read_only", 1);
      frm.set_df_property("department", "read_only", 1);
      frm.set_df_property("month", "read_only", 1);
      frm.set_df_property("year", "read_only", 1);
      frm.set_df_property("employee", "read_only", 1);
    }
  },
});
