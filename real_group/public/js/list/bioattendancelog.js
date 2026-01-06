frappe.listview_settings["BioAttendanceLog"] = {
  onload(listview) {
    // Remove Edit action from bulk actions
    listview.page.clear_actions_menu();
  },
};
