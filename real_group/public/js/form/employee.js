frappe.ui.form.on("Employee", {
  refresh(frm) {
    frm.set_query("holiday_list", () => {
      return {
        filters: {
          custom_branch: frm.doc.branch,
        },
      };
    });
    // Add a custom button if aadhaar number is use in multiple employees
    if (frm.doc.custom_aadhar_number) {
      frappe.db
        .get_list("Employee", {
          filters: [
            ["custom_aadhar_number", "=", frm.doc.custom_aadhar_number],
            ["name", "!=", frm.doc.name],
          ],
          fields: ["name"],
        })
        .then((records) => {
          if (records.length > 0) {
            frm.set_df_property("custom_linked_aadhaar", "hidden", 0);
            setTimeout(function () {
              let button = frm.fields_dict.custom_linked_aadhaar.$wrapper.find("button");
              window.applyCustomButtonStyle(button);
            }, 100);
          } else {
            frm.set_df_property("custom_linked_aadhaar", "hidden", 1);
          }
        });
    } else {
      frm.set_df_property("custom_linked_aadhaar", "hidden", 1); // hide if no Aadhar
    }

    if (frm.doc.pan_number) {
      frappe.db
        .get_list("Employee", {
          filters: [
            ["pan_number", "=", frm.doc.pan_number],
            ["name", "!=", frm.doc.name],
          ],
          fields: ["name"],
        })
        .then((records) => {
          if (records.length > 0) {
            frm.set_df_property("custom_linked_pan", "hidden", 0);
            setTimeout(function () {
              let button = frm.fields_dict.custom_linked_pan.$wrapper.find("button");
              window.applyCustomButtonStyle(button);
            }, 100);
          } else {
            frm.set_df_property("custom_linked_pan", "hidden", 1);
          }
        });
    } else {
      frm.set_df_property("custom_linked_pan", "hidden", 1); // hide if no Pan
    }

    frappe
      .call("get_employee_chart_data", {
        employee: frm.doc.name,
      })
      .then((resp) => {
        resp.message.factors.forEach((f) => {
          $(cur_frm.fields_dict["custom_bp_chart"].wrapper).append(
            `<div id="${f}"></div><div class="form-column col-sm-4">`
          );
          new frappe.Chart(`#${f}`, resp.message.charts[f]);
        });
      });

    if (!frm.doc.__islocal && frm.doc.custom_weekly_holiday_list) {
      frm.set_df_property("custom_weekly_holiday_list", "read_only", 1);
    }
  },

  company: function (frm) {
    if (frm.doc.company && frm.doc.company === "Real Ispat and Power Ltd") {
      frm.set_value("naming_series", "RB-EMP-UID");
    }
    if (frm.doc.company && frm.doc.company === "API Ispat and Powertech Private Limited") {
      frm.set_value("naming_series", "AP-EMP-UID");
    }
    if (frm.doc.company && frm.doc.company === "Shivalay Ispat and Power Private Limited") {
      frm.set_value("naming_series", "SH-EMP-UID");
    }
    if (frm.doc.company && frm.doc.company === "Real Ispat and Energy Private Limited") {
      frm.set_value("naming_series", "RI-EMP-UID");
    }

    if (frm.doc.company) {
      frappe.db.get_value("Company", frm.doc.company, "custom_epf_establishment_id").then((resp) => {
        cur_frm.set_value("custom_pf_number", resp.message.custom_epf_establishment_id);
      });
    } else {
      cur_frm.set_value("custom_pf_number", "");
    }
  },

  custom_linked_aadhaar: function (frm) {
    let is_hidden = frm.get_field("custom_linked_aadhaar").df.hidden;
    if (!is_hidden) {
      if (frm.doc.custom_aadhar_number) {
        frappe.db
          .get_list("Employee", {
            filters: [
              ["custom_aadhar_number", "=", frm.doc.custom_aadhar_number],
              ["name", "!=", frm.doc.name],
            ],
            fields: ["company", "name", "employee_name", "status", "custom_aadhar_number"],
          })
          .then(async (records) => {
            if (records.length > 0) {
              const data = await Promise.all(
                records.map(async (r) => {
                  const company_abbr = await frappe.db.get_value("Company", r.company, "abbr");
                  return {
                    company: company_abbr.message.abbr,
                    employee: r.name,
                    employee_name: r.employee_name,
                    status: r.status,
                    custom_aadhar_number: r.custom_aadhar_number,
                  };
                })
              );

              let dialog = new frappe.ui.Dialog({
                title: "Employees with Same Aadhar Number",
                size: "large",
                fields: [
                  {
                    fieldname: "employees",
                    fieldtype: "Table",
                    label: "Employees",
                    cannot_add_rows: true,
                    in_place_edit: false,
                    data: data,
                    get_data: () => data,
                    fields: [
                      {
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        label: "Company",
                        read_only: true,
                        in_list_view: true,
                        columns: 1.5,
                      },
                      {
                        fieldname: "employee",
                        fieldtype: "Link",
                        options: "Employee",
                        label: "Employee",
                        read_only: true,
                        in_list_view: true,
                        columns: 2,
                      },
                      {
                        fieldname: "status",
                        fieldtype: "Data",
                        label: "Status",
                        read_only: true,
                        in_list_view: true,
                        columns: 1.5,
                      },
                      {
                        fieldname: "custom_aadhar_number",
                        fieldtype: "Data",
                        label: "Aadhar Number",
                        read_only: true,
                        in_list_view: true,
                        columns: 2,
                      },
                    ],
                  },
                ],
                primary_action_label: "Close",
                primary_action() {
                  dialog.hide();
                },
              });

              dialog.show();
            }
          });
      }
    }
  },

  custom_linked_pan: function (frm) {
    let is_hidden = frm.get_field("custom_linked_pan").df.hidden;
    if (!is_hidden) {
      if (frm.doc.pan_number) {
        frappe.db
          .get_list("Employee", {
            filters: [
              ["pan_number", "=", frm.doc.pan_number],
              ["name", "!=", frm.doc.name],
            ],
            fields: ["company", "name", "employee_name", "status", "pan_number"],
          })
          .then(async (records) => {
            if (records.length > 0) {
              const data = await Promise.all(
                records.map(async (r) => {
                  const company_abbr = await frappe.db.get_value("Company", r.company, "abbr");
                  return {
                    company: company_abbr.message.abbr,
                    employee: r.name,
                    employee_name: r.employee_name,
                    status: r.status,
                    pan_number: r.pan_number,
                  };
                })
              );

              let dialog = new frappe.ui.Dialog({
                title: "Employees with Same PAN Number",
                size: "large",
                fields: [
                  {
                    fieldname: "employees",
                    fieldtype: "Table",
                    label: "Employees",
                    cannot_add_rows: true,
                    in_place_edit: false,
                    data: data,
                    get_data: () => data,
                    fields: [
                      {
                        fieldname: "company",
                        fieldtype: "Link",
                        options: "Company",
                        label: "Company",
                        read_only: true,
                        in_list_view: true,
                        columns: 1.5,
                      },
                      {
                        fieldname: "employee",
                        fieldtype: "Link",
                        options: "Employee",
                        label: "Employee",
                        read_only: true,
                        in_list_view: true,
                        columns: 2,
                      },
                      {
                        fieldname: "status",
                        fieldtype: "Data",
                        label: "Status",
                        read_only: true,
                        in_list_view: true,
                        columns: 1.5,
                      },
                      {
                        fieldname: "pan_number",
                        fieldtype: "Data",
                        label: "PAN Number",
                        read_only: true,
                        in_list_view: true,
                        columns: 2,
                      },
                    ],
                  },
                ],
                primary_action_label: "Close",
                primary_action() {
                  dialog.hide();
                },
              });

              dialog.show();
            }
          });
      }
    }
  },

  first_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.first_name);
    frm.set_value("first_name", capitalizedFirstName);
  },

  middle_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.middle_name);
    frm.set_value("middle_name", capitalizedFirstName);
  },

  last_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.last_name);
    frm.set_value("last_name", capitalizedFirstName);
  },

  employee_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.employee_name);
    frm.set_value("employee_name", capitalizedFirstName);
  },

  person_to_be_contacted(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.person_to_be_contacted);
    frm.set_value("person_to_be_contacted", capitalizedFirstName);
  },

  custom_additional_emegency_contact(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.custom_additional_emegency_contact);
    frm.set_value("custom_additional_emegency_contact", capitalizedFirstName);
  },

  permanent_address(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.permanent_address);
    frm.set_value("permanent_address", capitalizedFirstName);
  },

  current_address(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.current_address);
    frm.set_value("current_address", capitalizedFirstName);
  },

  custom_emergency_address(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.custom_emergency_address);
    frm.set_value("custom_emergency_address", capitalizedFirstName);
  },

  custom_additional_emergency_address(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.custom_additional_emergency_address);
    frm.set_value("custom_additional_emergency_address", capitalizedFirstName);
  },

  custom_father_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.custom_father_name);
    frm.set_value("custom_father_name", capitalizedFirstName);
  },

  custom_mother_name(frm) {
    let capitalizedFirstName = capitalizeWords(frm.doc.custom_mother_name);
    frm.set_value("custom_mother_name", capitalizedFirstName);
  },

  // ifsc_code(frm){
  //         let capitalizedFirstName = capitalizeWords(frm.doc.ifsc_code);
  //         frm.set_value('ifsc_code', capitalizedFirstName);
  // },

  custom_medical_history(frm) {
    frappe.call({
      method: "employee_medical_history",
      args: {
        e_name: frm.doc.name,
      },
      callback: function (r) {
        if (r.message && r.message.url) {
          window.location.href = r.message.url;
          // Optionally reload the page after a delay
          // setTimeout(function() {
          //     window.location.reload();
          // }, 1000);
        }
      },
    });
  },

  custom_same_as_permanent_address: function (frm) {
    if (frm.doc.custom_same_as_permanent_address === 1) {
      frm.set_value("current_address", frm.doc.permanent_address);
      frm.set_value("current_accommodation_type", frm.doc.permanent_accommodation_type);
      frm.set_value("custom_current_district", frm.doc.custom_permanent_district);
      frm.set_value("custom_current_city", frm.doc.custom_permanent_city);
      frm.set_value("custom_current_state", frm.doc.custom_permanent_state);
      frm.set_value("custom_current_country", frm.doc.custom_permanent_country);
      frm.set_value("custom_current_pin_code", frm.doc.custom_permanent_pin_code);
    } else {
      frm.set_value("current_address", "");
      frm.set_value("current_accommodation_type", "");
      frm.set_value("custom_current_district", "");
      frm.set_value("custom_current_city", "");
      frm.set_value("custom_current_state", "");
      frm.set_value("custom_current_country", "");
      frm.set_value("custom_current_pin_code", "");
    }
  },
});

window.applyCustomButtonStyle = function (button) {
  $(button).css({
    "background-color": "rgb(27, 56, 139)",
    color: "white",
    padding: "8px 12px",
    "border-radius": "10px",
    border: "none",
    cursor: "pointer",
  });
};

frappe.ui.form.on("Emergency Contacts", {
  refresh(frm) {
    // your code here
  },

  emergency_contact_name(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let capitalizedFirstName = capitalizeWords(row.emergency_contact_name);

    frappe.model.set_value(row.doctype, row.name, "emergency_contact_name", capitalizedFirstName);
  },
});

function capitalizeWords(str) {
  return str
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

frappe.ui.form.on("Employee Family Details", {
  refresh(frm) {
    // your code here
  },

  name1: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let capitalizedFirstName = capitalizeWords(row.name1);
    frappe.model.set_value(row.doctype, row.name, "name1", capitalizedFirstName);
  },
});

frappe.ui.form.on("Employee Nominee", {
  refresh(frm) {
    // your code here
  },
  nominee_name: function (frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    let capitalizedFirstName = capitalizeWords(row.nominee_name);
    frappe.model.set_value(row.doctype, row.name, "nominee_name", capitalizedFirstName);
  },
});
