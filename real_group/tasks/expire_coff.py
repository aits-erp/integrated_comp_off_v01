import frappe
from frappe.utils import today
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import (
    create_leave_ledger_entry,
)


def expire_unused_comp_off():
    today_date = today()

    # Comp requests expiring today (not already expired)
    requests = frappe.get_all(
        "Compensatory Leave Request",
        filters={
            "leave_expiry": today_date,
            "status": ["!=", "Expired"],
        },
        fields=["name", "employee", "credit"],
    )

    for req in requests:
        employee = req.employee
        credit = req.credit or 0

        if credit <= 0:
            continue

        # Actual remaining Comp Off balance from ledger
        balance = frappe.db.sql(
            """
            SELECT IFNULL(SUM(leaves), 0)
            FROM `tabLeave Ledger Entry`
            WHERE employee=%s
              AND leave_type='Compensatory Off'
              AND docstatus=1
            """,
            employee,
        )[0][0]

        if balance <= 0:
            # Nothing left to expire
            frappe.db.set_value(
                "Compensatory Leave Request",
                req.name,
                "status",
                "Expired",
            )
            continue

        # Only expire unused portion
        expire_qty = min(balance, credit)

        # Create negative ledger entry (this is the key)
        create_leave_ledger_entry(
            employee=employee,
            leave_type="Compensatory Off",
            leaves=-expire_qty,
            transaction_type="Leave Expiry",
            transaction_name=req.name,
        )

        # Mark request expired
        frappe.db.set_value(
            "Compensatory Leave Request",
            req.name,
            "status",
            "Expired",
        )

    frappe.db.commit()
