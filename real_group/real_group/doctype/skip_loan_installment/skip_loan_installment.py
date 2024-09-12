# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, get_first_day


class SkipLoanInstallment(Document):
	
	def before_save(self):
		if len(self.upcoming_installment) == 0:
			frappe.throw("Kindly Select the installment to Skip!!")


	def on_submit(self):
		
		if self.workflow_state == "Approved" and len(self.upcoming_installment) > 0:
			installments = self.upcoming_installment
			filtered_installment = [item for item in installments if item.get('skip') == 1]
			total_skip = len(filtered_installment)
			all_adds = frappe.db.get_list("Additional Salary", 
				filters = [
						["Additional Salary","ref_docname","=",self.active_loans],
						["Additional Salary","ref_doctype","=","Employee Advance"],
						["Additional Salary","payroll_date",">", self.posting_date]
						], 
				fields=['name', 'payroll_date'],
				order_by = 'payroll_date desc',
				limit = 1)
			last_date = str(all_adds[0].get("payroll_date"))
			# frappe.throw(str(last_date))
			last_installment_date = last_date
			# last_installment_date = installments[-1].get("installment_date")
			for rec in filtered_installment:
				if rec.amount == 0 or rec.amount < 0:
					frappe.throw(f"Installment Amount can not be 0 in row no {rec.idx}")
				ads = frappe.get_doc("Additional Salary", rec.additional_salary)
				ads.cancel()
				next_installment = get_first_day(add_to_date(last_installment_date, months = 1))
				additional_salary=frappe.get_doc(dict(
					amount = rec.amount,
					doctype = "Additional Salary",
					employee = self.employee,
					employee_name = self.employee_name,
					overwrite_salary_structure_amount = 0,
					ref_docname = self.active_loans,
					ref_doctype = "Employee Advance",
					salary_component = "Loan",
					payroll_date = next_installment,
					type = "Deduction",
					custom_skip_from_document = rec.additional_salary
					)
				)
				additional_salary.save()
				additional_salary.submit()
				last_installment_date = next_installment


@frappe.whitelist()
def get_additional_salary(employee,ref_doctype,ref_docname,posting_date):
	result = frappe.db.sql(f"""
		SELECT 
			name,
			amount,
			payroll_date,
			type,
			salary_component
		FROM
			`tabAdditional Salary`
		WHERE
			docstatus = 1
			AND employee = %s
			AND ref_doctype = %s
			AND ref_docname = %s
			AND payroll_date >= %s
		ORDER BY
			payroll_date ASC
	""",(employee, ref_doctype, ref_docname, posting_date), as_dict=1)

	return result


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employee_advance(doctype, txt, searchfield, start, page_len, filters):
	employee = filters.get("employee")
	values = {"employee": employee, "docstatus": 1, "txt":txt}

	return frappe.db.sql("""
		SELECT name
		FROM `tabEmployee Advance`
		WHERE docstatus = 1 
			AND employee = %(employee)s
			AND return_amount != advance_amount
	""", values=values, as_dict = 0)