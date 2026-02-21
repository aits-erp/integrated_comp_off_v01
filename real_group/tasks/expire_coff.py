import frappe
from frappe.utils import flt, today


def create_comp_off_expiry_ledger(
    employee,
    employee_name,
    company,
    expire_qty,
    date,
    transaction_type,
    transaction_name,
):
    doc = frappe.get_doc(
        {
            "doctype": "Leave Ledger Entry",
            "employee": employee,
            "employee_name": employee_name,
            "company": company,
            "leave_type": "Compensatory Off",
            "transaction_type": transaction_type,
            "transaction_name": transaction_name,
            "leaves": -expire_qty,
            "from_date": date,
            "to_date": date,
            "is_expired": 1,
            "is_carry_forward": 0,
            "is_lwp": 0,
        }
    )

    doc.flags.ignore_permissions = 1
    doc.flags.ignore_links = 1

    doc.insert()
    doc.submit()


def get_allocation_balance(employee: str, allocation_name: str) -> float:
    """Returns current remaining C-off balance for a specific Leave Allocation."""
    if not allocation_name:
        return 0.0

    balance = frappe.db.sql(
        """
        SELECT IFNULL(SUM(leaves), 0)
        FROM `tabLeave Ledger Entry`
        WHERE employee=%s
          AND leave_type='Compensatory Off'
          AND transaction_type='Leave Allocation'
          AND transaction_name=%s
          AND docstatus=1
        """,
        (employee, allocation_name),
    )[0][0]
    return flt(balance)


def mark_request_expired(
    request_name: str,
    has_custom_is_expired: bool = False,
    has_custom_expired_leaves: bool = False,
    has_custom_balance: bool = False,
    expired_qty: float = 0.0,
) -> None:
    frappe.db.set_value("Compensatory Leave Request", request_name, "status", "Expired")

    if has_custom_is_expired:
        frappe.db.set_value("Compensatory Leave Request", request_name, "custom_is_expired", 1)

    if has_custom_expired_leaves and expired_qty > 0:
        existing_expired = flt(
            frappe.db.get_value("Compensatory Leave Request", request_name, "custom_expired_leaves") or 0
        )
        frappe.db.set_value(
            "Compensatory Leave Request",
            request_name,
            "custom_expired_leaves",
            existing_expired + flt(expired_qty),
        )

    if has_custom_balance:
        frappe.db.set_value("Compensatory Leave Request", request_name, "custom_balance", 0)


def expire_unused_comp_off():
    today_date = today()
    clr_meta = frappe.get_meta("Compensatory Leave Request")
    has_custom_balance = clr_meta.has_field("custom_balance")
    has_custom_is_expired = clr_meta.has_field("custom_is_expired")
    has_custom_expired_leaves = clr_meta.has_field("custom_expired_leaves")

    requests = frappe.get_all(
        "Compensatory Leave Request",
        filters={
            "expiry": today_date,
            "status": ["!=", "Expired"],
        },
        fields=["name", "employee", "credit", "leave_allocation"],
    )

    for req in requests:
        employee = req.employee
        if has_custom_is_expired:
            is_already_expired = frappe.db.get_value("Compensatory Leave Request", req.name, "custom_is_expired")
            if is_already_expired:
                mark_request_expired(
                    req.name,
                    has_custom_is_expired=has_custom_is_expired,
                    has_custom_expired_leaves=has_custom_expired_leaves,
                    has_custom_balance=has_custom_balance,
                )
                continue

        request_balance = flt(req.credit or 0)
        if has_custom_balance:
            request_balance = flt(frappe.db.get_value("Compensatory Leave Request", req.name, "custom_balance") or 0)

        if request_balance <= 0:
            mark_request_expired(
                req.name,
                has_custom_is_expired=has_custom_is_expired,
                has_custom_expired_leaves=has_custom_expired_leaves,
                has_custom_balance=has_custom_balance,
            )
            continue

        if not req.leave_allocation:
            frappe.log_error(
                title="C-off Expiry Skipped (Missing Leave Allocation)",
                message=f"Compensatory Leave Request {req.name} has no leave_allocation; marking as expired.",
            )
            mark_request_expired(
                req.name,
                has_custom_is_expired=has_custom_is_expired,
                has_custom_expired_leaves=has_custom_expired_leaves,
                has_custom_balance=has_custom_balance,
            )
            continue

        allocation_balance = get_allocation_balance(employee, req.leave_allocation)
        if allocation_balance <= 0:
            mark_request_expired(
                req.name,
                has_custom_is_expired=has_custom_is_expired,
                has_custom_expired_leaves=has_custom_expired_leaves,
                has_custom_balance=has_custom_balance,
            )
            continue

        expire_qty = min(allocation_balance, request_balance)
        if expire_qty <= 0:
            mark_request_expired(
                req.name,
                has_custom_is_expired=has_custom_is_expired,
                has_custom_expired_leaves=has_custom_expired_leaves,
                has_custom_balance=has_custom_balance,
            )
            continue

        employee_doc = frappe.db.get_value(
            "Employee",
            employee,
            ["employee_name", "company"],
            as_dict=True,
        )

        create_comp_off_expiry_ledger(
            employee=employee,
            employee_name=employee_doc.employee_name,
            company=employee_doc.company,
            expire_qty=expire_qty,
            date=today_date,
            transaction_type="Leave Allocation",
            transaction_name=req.leave_allocation,
        )

        mark_request_expired(
            req.name,
            has_custom_is_expired=has_custom_is_expired,
            has_custom_expired_leaves=has_custom_expired_leaves,
            has_custom_balance=has_custom_balance,
            expired_qty=expire_qty,
        )

    frappe.db.commit()
