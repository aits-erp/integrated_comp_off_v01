import frappe 

def execute():
    add_index = {
        "Attendance":["attendance_date","attendance_request","employee","custom_reprocess_reference"],
        "Employee Checkin":["attendance"]
    }
    for doctype, fields in add_index.items():
        frappe.db.add_index(doctype, fields)
