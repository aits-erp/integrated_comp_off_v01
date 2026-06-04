frappe.ui.form.on("Salary Structure Assignment", {
  refresh(frm) {
    frm.set_df_property("custom_basic_pay", "read_only", 1);
    frm.set_df_property("base", "read_only", 1);
    set_values_from_salary_structure(frm);
  },

  salary_structure(frm) {
    set_values_from_salary_structure(frm);
  },
});

function set_values_from_salary_structure(frm) {
  if (!frm.doc.salary_structure || frm.doc.docstatus === 1) {
    return;
  }

  frappe.call({
    method: "real_group.doc_events.salary_structure_assignment.get_salary_structure_assignment_values",
    args: {
      salary_structure: frm.doc.salary_structure,
    },
    callback(r) {
      if (!r.exc) {
        const values = r.message || {};
        frm.set_value("custom_basic_pay", values.basic_pay || 0);
        frm.set_value("base", values.base || 0);
      }
    },
  });
}
