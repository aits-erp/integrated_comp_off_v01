frappe.ui.form.on("Leave Type", {
  refresh: function (frm) {
    if (frm.doc.custom_calculate_based_on_working_days) {
      frm.set_df_property("earned_leave_frequency", "hidden", 1);
      frm.set_df_property("allocate_on_day", "hidden", 1);
    } else {
      frm.set_df_property("earned_leave_frequency", "hidden", 0);
      frm.set_df_property("allocate_on_day", "hidden", 0);
    }
  },
  custom_calculate_based_on_working_days: function (frm) {
    if (frm.doc.custom_calculate_based_on_working_days) {
      frm.set_df_property("earned_leave_frequency", "hidden", 1);
      frm.set_df_property("allocate_on_day", "hidden", 1);
    } else {
      frm.set_df_property("earned_leave_frequency", "hidden", 0);
      frm.set_df_property("allocate_on_day", "hidden", 0);
    }
  },
});
