frappe.ui.form.on("Shift Type", {
  refresh(frm) {
    frm.remove_custom_button("Mark Attendance");
  },
  validate(frm) {
    if (frm.doc.start_time && frm.doc.end_time) {
      const start = toFloat(frm.doc.start_time);
      const end = toFloat(frm.doc.end_time);
      if (end < start) {
        frm.set_value("custom_is_cross_day", 1);
      }
    }
  },
});

function toFloat(str) {
  const [h, m, s] = str.split(":").map(Number);
  return h * 3600 + m * 60 + s;
}
