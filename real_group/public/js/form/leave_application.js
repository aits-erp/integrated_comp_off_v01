frappe.ui.form.on("Leave Application", {
  from_date: function (frm) {
    validate_dates(frm);
  },

  to_date: function (frm) {
    validate_dates(frm);
  },
  half_day: function (frm) {
    if (frm.doc.half_day === 0) {
      frm.set_value("custom_half_type", "");
    }
    if (frm.doc.half_day && frm.doc.to_date != frm.doc.from_date) {
      frm.set_df_property("half_day_date", "reqd", 1);
    }
  },

  leave_type: function (frm) {
    if (frm.doc.leave_type == "Only Gate Pass") {
      frm.set_value("custom_skip_gate_pass", 0);
    }
  },

  before_workflow_action: (frm) => {
    if (frm.doc.custom_reject_reason === "") {
      frappe.throw("set reason");
    }
    if (frm.selected_workflow_action == "Reject") {
      let dialog = new frappe.ui.Dialog({
        title: "Reason for Rejection",
        fields: [
          {
            label: "Reason",
            fieldname: "reject_reason",
            fieldtype: "Link",
            options: "Reject Reason",
            reqd: 1,
            get_query: function () {
              return {
                filters: [["Reject Reason Type", "document_type", "=", frm.doc.doctype]],
              };
            },
          },
        ],
        primary_action_label: "Reject",
        primary_action(values) {
          if (values.reject_reason !== "") {
            frappe
              .call({
                method: "set_reject_reason",
                args: {
                  doctype: frm.doc.doctype,
                  doc_name: frm.doc.name,
                  reject_reason: values.reject_reason,
                  workflow_state: frm.doc.workflow_state,
                },
                freeze: true,
                async: false,
              })
              .then((res) => {
                if (res.status == "false") {
                  frappe.throw(res.message.message);
                } else {
                  frappe.msgprint(res.message.message);
                  setTimeout(function () {
                    window.location.reload();
                  }, 2000);
                }
              });

            dialog.hide();
          } else {
            frappe.throw("Hi");
          }
        },
      });
      dialog.show();
    }
  },
});

function validate_dates(frm) {
  if (frm.doc.from_date || frm.doc.to_date) {
    if (!frm.doc.employee) {
      frm.set_value("from_date", "");
      frm.set_value("to_date", "");
      frappe.throw(__("Please select Employee before setting dates"));
    }
    if (!frm.doc.leave_type) {
      frm.set_value("from_date", "");
      frm.set_value("to_date", "");
      frappe.throw(__("Please select Leave Type before setting dates"));
    }
  }
}
