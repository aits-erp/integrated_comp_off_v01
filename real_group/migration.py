import frappe


INDEX_SPECS = (
    ("Employee Checkin", "idx_ec_attendance", ("attendance",)),
    ("Attendance", "idx_att_emp_date_doc", ("employee", "attendance_date", "docstatus")),
    ("Attendance Request", "idx_ar_emp_doc_from_to", ("employee", "docstatus", "from_date", "to_date")),
    ("Incentive Log", "idx_il_emp_work_doc", ("employee", "work_date", "docstatus")),
    ("Compensatory Leave Request", "idx_clr_emp_work_doc", ("employee", "work_from_date", "work_end_date", "docstatus")),
    ("Short Leave", "idx_sl_emp_date_doc", ("employee", "for_date", "docstatus")),
)


def ensure_reprocess_indexes():
    for doctype, index_name, columns in INDEX_SPECS:
        if _has_index(doctype, index_name) or _has_equivalent_index(doctype, columns):
            continue
        frappe.db.add_index(doctype, list(columns), index_name=index_name)


def _has_index(doctype: str, index_name: str) -> bool:
    return bool(frappe.db.has_index(f"tab{doctype}", index_name))


def _has_equivalent_index(doctype: str, columns: tuple[str, ...]) -> bool:
    rows = frappe.db.sql(f"SHOW INDEX FROM `tab{doctype}`", as_dict=True)
    target = tuple(columns)
    indexes = {}
    for row in rows:
        key = row.get("Key_name")
        seq = int(row.get("Seq_in_index") or 0)
        col = row.get("Column_name")
        if not key or not seq or not col:
            continue
        indexes.setdefault(key, {})[seq] = col

    for parts in indexes.values():
        ordered = tuple(parts[i] for i in sorted(parts))
        if ordered == target:
            return True

    return False
