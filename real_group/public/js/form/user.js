frappe.ui.form.on("User", {
  refresh(frm) {
    if (frm.doc.username) {
      frm.add_custom_button(__("Set Employee"), function () {
        frappe.prompt(
          {
            label: "Employee",
            fieldname: "employee",
            fieldtype: "Link",
            options: "Employee",
          },
          (values) => {
            frappe.call({
              method: "set_user",
              args: {
                employee: values.employee,
                user: frm.doc.name,
              },
              freeze: true,
              freeze_message: "Please Wait",
              callback: function (r) {
                if (!r.exc) {
                  frappe.msgprint(r.message);
                } else {
                  frappe.msgprint("Something went wrong, check logs");
                }
              },
            });
          }
        );
      });
    }
  },
});
