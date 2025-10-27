frappe.ui.form.on("Leave Type", {
  custom_calculate_based_on_working_days: function (frm) {
    if (frm.doc.custom_calculate_based_on_working_days) {
      frm.set_df_property("earned_leave", "hidden", 1);
      frm.set_value("is_earned_leave", 0);
    } else {
      frm.set_df_property("earned_leave", "hidden", 0);
    }
  },
});
