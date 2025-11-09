frappe.ui.form.on("Employee Transfer", {
  refresh: function (frm) {
    frm.fields_dict.custom_employee_leave.grid.grid_buttons.hide();
  },
  employee: function (frm) {
    if (frm.doc.employee) {
      frm.trigger("reallocate_leaves");
    }
  },
  reallocate_leaves: function (frm) {
    if (frm.doc.reallocate_leaves) {
      frm.trigger("get_leave_info");
    }
  },
  get_leave_info: function (frm) {
    if (!frm.doc.employee) {
      frappe.throw(__("Please select an Employee first."));
    }
    frappe.call({
      method: "hrms.hr.doctype.leave_application.leave_application.get_leave_details",
      args: { employee: frm.doc.employee, date: frappe.datetime.get_today() },
      callback: function (r) {
        if (r.message) {
          const data = r.message.leave_allocation;
          frm.clear_table("custom_employee_leave");
          $.each(data, function (i, d) {
            var child = frm.add_child("custom_employee_leave", {
              existing_leave_type: i,
              number_of_leaves: d.remaining_leaves,
            });
            frm.fields_dict.custom_employee_leave.grid.toggle_enable("existing_leave_type", false);
          });
          frm.refresh_field("custom_employee_leave");
          frm.fields_dict.custom_employee_leave.grid.grid_buttons.hide();
        }
      },
    });
  },
});

frappe.ui.form.on("Employee Leave Transfer", {
  expire: function (frm, cdt, cdn) {
    console.log(cdt, cdn);
    var row = locals[cdt][cdn];
    if (row.expire) {
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_editable(
        "number_of_leaves",
        false
      );
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_editable("new_leave_type", false);

      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_reqd("number_of_leaves", false);
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_reqd("new_leave_type", false);
    } else {
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_editable("number_of_leaves", true);
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_editable("new_leave_type", true);

      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_reqd("number_of_leaves", true);
      frm.fields_dict["custom_employee_leave"].grid.grid_rows_by_docname[cdn].toggle_reqd("new_leave_type", true);
    }
  },
});
