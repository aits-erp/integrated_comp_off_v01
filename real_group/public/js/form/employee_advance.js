frappe.ui.form.on("Employee Advance", {
  refresh(frm) {
    if (frm.doc.employee) {
      frm.trigger("get_emp_advance");
    }

    frm.set_query("custom_guarantor_one", function () {
      return {
        query: "real_group.real_group.utils.get_employees",
        filters: {
          employee: frm.doc.employee,
        },
      };
    });
    frm.set_query("custom_guarantor_two", function () {
      return {
        query: "real_group.real_group.utils.get_employees",
        filters: {
          employee: frm.doc.employee,
        },
      };
    });
  },

  before_workflow_action: (frm) => {
    console.log(frm.selected_workflow_action);

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
          if (values.reject_reason) {
            frappe
              .call({
                method: "set_reject_reason",
                args: {
                  doctype: frm.doc.doctype,
                  doc_name: frm.doc.name,
                  reject_reason: values.reject_reason,
                  workflow_state: frm.doc.workflow_state,
                  freeze: true,
                },
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
          }
        },
      });
      dialog.show();
    }
  },

  employee: function (frm) {
    frm.trigger("get_emp_advance");
  },

  get_emp_advance(frm) {
    if (frm.doc.employee) {
      frappe.call({
        method: "real_group.real_group.utils.employee_advance_details",
        args: {
          today: frm.doc.posting_date,
          employee: frm.doc.employee,
        },
        callback: function (r) {
          if (!r.exc) {
            let html_table = r.message;
            cur_frm.fields_dict.custom_previous_salary.$wrapper.empty();
            cur_frm.fields_dict.custom_previous_salary.$wrapper.append(html_table);
          }
        },
      });
      frappe.call({
        method: "real_group.real_group.utils.existing_loan_summary",
        args: {
          today: frm.doc.posting_date,
          employee: frm.doc.employee,
        },
        callback: function (r) {
          if (!r.exc) {
            let html_table = r.message;
            cur_frm.fields_dict.custom_previous_loans.$wrapper.empty();
            cur_frm.fields_dict.custom_previous_loans.$wrapper.append(html_table);
          }
        },
      });
    }
  },
  advance_amount: function (frm) {
    frm.trigger("set_installement_amount");
  },

  custom_requested_amount: function (frm) {
    frm.trigger("set_installement_amount");
  },
  custom_installment_amount: function (frm) {
    frm.trigger("set_installement_amount");
  },

  set_installement_amount: function (frm) {
    if (frm.doc.advance_amount == 0) {
      const custom_requested_amount = frm.doc.custom_requested_amount || 0;
      const custom_installment_amount = frm.doc.custom_installment_amount || 1;

      let custom_number_of_installments = Math.floor(custom_requested_amount / custom_installment_amount);
      if (custom_requested_amount % custom_installment_amount !== 0) {
        custom_number_of_installments += 1;
      }
      frm.set_value("custom_number_of_installments", custom_number_of_installments);
    } else {
      const advance_amount = frm.doc.advance_amount || 0;
      const custom_installment_amount = frm.doc.custom_installment_amount || 1;

      let custom_number_of_installments = Math.floor(advance_amount / custom_installment_amount);
      if (advance_amount % custom_installment_amount !== 0) {
        custom_number_of_installments += 1;
      }
      frm.set_value("custom_number_of_installments", custom_number_of_installments);
    }
  },
});
