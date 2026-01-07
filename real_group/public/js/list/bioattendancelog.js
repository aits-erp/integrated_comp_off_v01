frappe.listview_settings["BioAttendanceLog"] = {
  refresh(listview) {
    listview.page.clear_actions_menu();

    const allowedRoles = ["HR User", "HR Manager", "Payroll-CREASX", "Payroll-R"];

    const canResetLogs = allowedRoles.some((role) => frappe.user.has_role(role));

    if (!canResetLogs) return;
    listview.page.add_inner_button(__("Reset Logs"), async () => resetLogs(listview));
  },
};

function resetLogs(listview) {
  const logNames = listview.get_checked_items(true);

  if (!logNames.length) {
    frappe.msgprint(__("Select at least one log to reset."));
    return;
  }

  frappe.confirm(__("Set Is Processed to N for the selected logs?"), async () => {
    const { message } = await frappe.call({
      method: "real_group.real_group.doctype.bioattendancelog.bioattendancelog.reset_bioattendance_logs",
      args: { log_names: logNames },
      freeze: true,
      freeze_message: __("Resetting selected logs..."),
    });

    frappe.show_alert({
      message: __("Reset {0} log(s).", [message?.updated || 0]),
      indicator: "green",
    });

    listview.refresh();
  });
}
