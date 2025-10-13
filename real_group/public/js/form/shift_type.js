frappe.ui.form.on("Shift Type", {
  refresh(frm) {
    frm.remove_custom_button("Mark Attendance");
  },
});
