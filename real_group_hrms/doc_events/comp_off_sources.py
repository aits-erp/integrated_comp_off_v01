import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate


def assign_comp_off_sources_fifo(doc, method=None):
	"""Record FIFO source quantities; the HRMS ledger remains authoritative."""
	if not doc.leave_type or not frappe.db.get_value("Leave Type", doc.leave_type, "is_compensatory"):
		doc.set("custom_comp_off_source_request", [])
		doc.custom_comp_off_available_work_date = ""
		return
	if not doc.employee or not doc.from_date:
		return
	old = doc.get_doc_before_save() if not doc.is_new() else None
	if old and old.docstatus == 1:
		return
	needed = flt(doc.total_leave_days, 6)
	if needed <= 0:
		frappe.throw(_("Compensatory Off leave days must be greater than zero."))
	# Serialize assignments for this employee, including competing draft saves.
	frappe.db.sql("select name from `tabEmployee` where name=%s for update", doc.employee)
	meta = frappe.get_meta("Compensatory Leave Request")
	if not meta.has_field("credit"):
		frappe.throw(_("Compensatory Leave Request has no credit field. Configure actual earned quantities before using FIFO."), title=_("Comp Off Setup Required"))
	fields = ["name", "work_from_date", "work_end_date", "credit", "creation"]
	for field in ("expiry", "custom_is_expired", "status"):
		if meta.has_field(field):
			fields.append(field)
	requests = frappe.get_all("Compensatory Leave Request", filters={"employee": doc.employee, "leave_type": doc.leave_type, "docstatus": 1, "work_end_date": ["<", doc.from_date]}, fields=fields, order_by="work_end_date asc, work_from_date asc, creation asc, name asc")
	unmapped = frappe.db.sql("""
		select a.name from `tabLeave Application` a
		where a.employee=%s and a.leave_type=%s and a.name!=%s
		  and (a.docstatus=0 or (a.docstatus=1 and a.status='Approved'))
		  and not exists (select 1 from `tabComp Off Source Request` s
		      where s.parent=a.name and s.parenttype='Leave Application'
		      and s.parentfield='custom_comp_off_source_request') limit 1
	""", (doc.employee, doc.leave_type, doc.name or ""))
	if unmapped:
		frappe.throw(_("Comp Off application {0} has no source mapping. Reconcile historical applications before assigning credits.").format(unmapped[0][0]), title=_("Comp Off Reconciliation Required"))
	rows = frappe.db.sql("""
		select s.compensatory_leave_request, s.allocated_days, a.name
		from `tabComp Off Source Request` s join `tabLeave Application` a on a.name=s.parent
		where a.employee=%s and a.leave_type=%s and a.name!=%s
		  and s.parenttype='Leave Application' and s.parentfield='custom_comp_off_source_request'
		  and (a.docstatus=0 or (a.docstatus=1 and a.status='Approved'))
	""", (doc.employee, doc.leave_type, doc.name or ""), as_dict=True)
	used = {}
	for row in rows:
		amount = flt(row.allocated_days, 6)
		if amount <= 0:
			frappe.throw(_("Comp Off application {0} has a source without a valid quantity. Reconciliation is required.").format(row.name), title=_("Comp Off Reconciliation Required"))
		used[row.compensatory_leave_request] = used.get(row.compensatory_leave_request, 0) + amount
	assignments = []
	for request in requests:
		if request.get("custom_is_expired") or request.get("status") == "Expired":
			continue
		if request.get("expiry") and getdate(request.expiry) < getdate(doc.from_date):
			continue
		available = flt(flt(request.credit, 6) - used.get(request.name, 0), 6)
		if available < 0:
			frappe.throw(_("Allocated quantities exceed credit on {0}. Reconciliation is required.").format(request.name), title=_("Comp Off Reconciliation Required"))
		amount = min(needed, available)
		if amount > 0:
			assignments.append((request, amount))
			needed = flt(needed - amount, 6)
		if needed <= 0:
			break
	if needed > 0:
		frappe.throw(_("Insufficient reconciled, unexpired Comp Off sources; {0} day(s) could not be assigned. Check existing ledger and history.").format(needed), title=_("Comp Off Reconciliation Required"))
	doc.set("custom_comp_off_source_request", [])
	for request, amount in assignments:
		doc.append("custom_comp_off_source_request", {"compensatory_leave_request": request.name, "allocated_days": amount})
	doc.custom_comp_off_available_work_date = ", ".join(formatdate(request.work_from_date) for request, amount in assignments)
