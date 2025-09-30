frappe.ui.form.on("Appraisal Template", {
  setup(frm) {
    frm.get_field("custom_appraiser_feedback_criteria").grid.editable_fields = [
      { fieldname: "feedback_criteria", columns: 11 },
    ];
  },
});
