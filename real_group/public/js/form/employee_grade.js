frappe.ui.form.on("Employee Grade", {
  refresh(frm) {
    frm.set_query("custom_allowed_check_in_machines", function (doc, cdt, cdn) {
      return {
        filters: {
          machine_type: "In",
        },
      };
    });
    frm.set_query("custom_allowed_check_out_machines", function (doc, cdt, cdn) {
      return {
        filters: {
          machine_type: "Out",
        },
      };
    });
  },

  custom_present_on_holiday: function (frm) {
    frm.set_value("custom_extra_work_hour", frm.doc.custom_present_on_holiday);
    if (frm.doc.custom_present_on_holiday == "Comp Off") {
      frm.set_value("custom_incentive_gross_amount", 0);
      frm.set_value("custom_incentive_ceiling", 0);
    }
  },

  custom_no_punch_applicable: function (frm) {
    frm.events.hide_short_leave_section(frm);
  },

  custom_single_punch_applicable: function (frm) {
    frm.events.hide_short_leave_section(frm);
  },
  custom_extra_work_hour: function (frm) {
    if (frm.doc.custom_present_on_holiday == "Comp Off") {
      frm.set_value("custom_incentive_gross_amount", 0);
      frm.set_value("custom_incentive_ceiling", 0);
    }
  },
  hide_short_leave_section: function (frm) {
    if (frm.doc.custom_no_punch_applicable == 1 || frm.doc.custom_single_punch_applicable == 1) {
      frm.set_df_property("custom_short_leave_type", "hidden", 1);
      frm.set_df_property("custom_no_of_times", "hidden", 1);
      frm.set_df_property("custom_hours_per_time", "hidden", 1);
    } else {
      frm.set_value("custom_short_leave_type", "");
      frm.set_value("custom_no_of_times", "");
      frm.set_value("custom_hours_per_time", "");
      frm.set_df_property("custom_short_leave_type", "hidden", 0);
      frm.set_df_property("custom_no_of_times", "hidden", 0);
      frm.set_df_property("custom_hours_per_time", "hidden", 0);
    }
  },
});
