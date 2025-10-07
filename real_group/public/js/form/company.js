frappe.ui.form.on("Company", {
  refresh(frm) {
    if (frappe.user.has_role("System Manager")) {
      frm.add_custom_button("Reset Employee Code", function () {
        let d = new frappe.ui.Dialog({
          title: "Enter Starting and Ending Code",
          fields: [
            {
              label: "Employee Code Starting From",
              fieldname: "starting_from",
              fieldtype: "Int",
              reqd: 1,
            },
            {
              label: "Employee Code Ending At",
              fieldname: "ending_at",
              fieldtype: "Int",
              reqd: 1,
            },
          ],
          size: "small", // small, large, extra-large
          primary_action_label: "Reset",
          primary_action(values) {
            frappe
              .call("reset_employee_code", {
                starting_from: values.starting_from,
                ending_at: values.ending_at,
                company: frm.doc.name,
              })
              .then((resp) => {
                if (resp.message.status == false) {
                  frappe.throw(resp.message.message);
                } else {
                  frappe.msgprint(resp.message.message);
                }
              });
          },
        });

        d.show();
      });
    }
  },
});
