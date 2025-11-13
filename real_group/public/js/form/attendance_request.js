frappe.templates["existing_leave.html"] = `
<div class="form-message yellow">
  <div>{{__("There are existing leaves on the selected date range.")}}</div>
</div>
<table class="table table-bordered table-hover">
  <thead>
    <tr>
      <th style="width: 20%">{{ __("Name") }}</th>
      <th style="width: 20%">{{ __("From Date") }}</th>
      <th style="width: 20%">{{ __("To Date") }}</th>
      <th style="width: 20%">{{ __("Is Half Day") }}</th>
      <th style="width: 20%">{{ __("Half Day Date") }}</th>
      <th style="width: 20%">{{ __("Status") }}</th>
    </tr>
  </thead>

  <tbody>
    {% for(var i=0; i < leaves.length; i++) { %} <tr>
      <td class="small"><a href="{{ frappe.utils.get_form_link("Leave Application",leaves[i].name) }}">{{ leaves[i].name }}</a></td>
      <td class="small"> {{ __(leaves[i].from_date) }} </td>
      <td class="small"> {{ __(leaves[i].to_date) }} </td>
      <td class="small"> {{ __(leaves[i].half_day ? "Yes" : "No") }} </td>
      <td class="small"> {{ __(leaves[i].half_day_date) }} </td>
      <td class="small"> {{ __(leaves[i].status) }} </td>
      </tr>
      {% } %}
  </tbody>
</table>`;

frappe.ui.form.on("Attendance Request", {
  custom_from_time: (frm) => {
    if (!frm.doc.from_date || !frm.doc.employee || !frm.doc.custom_from_time) return;
    frappe.call({
      method: "real_group.api.attendance_request.closest_shift_for_time",
      args: {
        time: frm.doc.custom_from_time,
        date: frm.doc.from_date,
        employee: frm.doc.employee,
      },
      callback: function (r) {
        if (r.message) {
          frm.set_value("shift", r.message);
          frm.set_df_property("shift", "read_only", 1);
        }
      },
    });
  },
  before_workflow_action: (frm) => {
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
  half_day: (frm) => {
    if (frm.doc.half_day && frm.doc.to_date == frm.doc.from_date) {
      frm.set_value("half_day_date", frm.doc.from_date);
    } else {
      frm.set_value("half_day_date", null);
    }
  },
  to_date: (frm) => {
    if (frm.doc.half_day) {
      frm.set_value("half_day_date", null);
    }
  },
  refresh: (frm) => {
    if (frm.doc.from_date && frm.doc.to_date && frm.doc.employee) {
      frappe.call({
        method: "real_group.api.attendance_request.get_leave_on_dates",
        args: {
          employee: frm.doc.employee,
          from_date: frm.doc.from_date,
          to_date: frm.doc.to_date,
        },
        callback: function (r) {
          if (r.message) {
            const leaves = r.message;
            if (leaves.length < 1) return;
            frm.dashboard.add_section(
              frappe.render_template("existing_leave.html", {
                leaves: r.message || [],
              }),
              __("Existing Leaves")
            );
          }
        },
      });
    }
  },
});
