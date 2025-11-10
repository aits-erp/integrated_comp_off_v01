frappe.ui.form.on("Leave Application", {
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

  to_date: function (frm) {
    if (!frm.doc.from_date || !frm.doc.to_date || !frm.doc.employee) {
      return;
    }
    if (frm.doc.to_date == frm.doc.from_date) {
      frappe.call({
        method: "real_group.utils.is_holiday_for_employee",
        args: {
          employee: frm.doc.employee,
          date: frm.doc.to_date,
        },
        freeze: true,
        callback: function (r) {
          if (r.message) {
            const data = r.message;
            if (data.is_half_day) {
              frm.set_value("half_day", 1);
              frm.set_df_property("half_day", "read_only", 1);
              frm.set_df_property("half_day", "description", " (Auto set as it is half day holiday on this date.)");
            }
          }
        },
      });
    } else {
      frappe.call({
        method: "real_group.utils.find_half_day",
        args: {
          employee: frm.doc.employee,
          from_date: frm.doc.from_date,
          to_date: frm.doc.to_date,
        },
        freeze: true,
        callback: function (r) {
          if (r.message) {
            const date = r.message;
            if (date) {
              frm.set_value("half_day", 1);
              setInterval(() => {
                frm.set_value("half_day_date", date);
                frm.set_value("half_day_date", date);
                frm.set_df_property("half_day_date", "read_only", 1);
              }, 100);
              frm.set_df_property("half_day", "read_only", 1);
              frm.set_df_property("half_day", "description", " (Auto set as there is half day holiday in this range.)");
            }
          }
        },
      });
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
