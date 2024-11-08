import frappe
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip as ss

def process_arrear(self, *args, **kwargs):

	pass

# 	ssa_list = frappe.db.get_list(
# 		"Salary Structure Assignment", 
# 		filters={"employee": self.employee, "docstatus": 1}, 
# 		order_by="creation DESC"
# 	)
# 	if len(ssa_list) > 0:
# 		ssa_doc = frappe.get_doc("Salary Structure Assignment", ssa_list[0].name)
# 		factor = self.base/ssa_doc.base
		
# 		sal_slip_list = frappe.db.get_list(
# 			"Salary Slip", 
# 			filters={
# 				"employee": self.employee,
# 				"creation": ["between", [ssa_doc.creation, frappe.utils.add_to_date(frappe.utils.today(), days=-1)]],
# 				"docstatus": 1
# 			}
# 		)

# 		total_arrears = 0
# 		my_list = []
# 		for slip in sal_slip_list:
# 			sal_slip_doc = frappe.get_doc("Salary Slip", slip.name)
# 			for earning in sal_slip_doc.earnings:
# 				earning.custom_revised_amount = factor * earning.amount
# 				frappe.db.set_value("Salary Detail", earning.name, 'custom_revised_amount',  factor*earning.amount)
# 				frappe.db.set_value("Salary Detail", earning.name, 'custom_arrears_difference',  factor*earning.amount - earning.amount)
			
# 			for deduction in sal_slip_doc.deductions:
# 				deduction.custom_revised_amount = factor * deduction.amount
# 				frappe.db.set_value("Salary Detail", deduction.name, 'custom_revised_amount',  factor*deduction.amount)
# 				frappe.db.set_value("Salary Detail", deduction.name, 'custom_arrears_difference',  factor*deduction.amount - deduction.amount)

# 			sal_slip_doc.custom_gross_arrears = sal_slip_doc.gross_pay * factor
# 			sal_slip_doc.custom_total_deduction_arrears = sal_slip_doc.total_deduction * factor	
# 			sal_slip_doc.custom_net_pay_arrears = sal_slip_doc.net_pay * factor
# 			total_arrears += sal_slip_doc.net_pay * factor - sal_slip_doc.net_pay	
	
# 			sal_slip_doc.save()
		
# 		arrear_doc = frappe.new_doc("Additional Salary")
# 		arrear_doc.update(
# 			{
# 				"doctype": "Additional Salary",
# 				"employee": self.employee,
# 				"payroll_date": self.from_date,
# 				"salary_component": "Arrear",
# 				"amount": total_arrears,

# 			}
# 		).save()
# 		arrear_doc.submit()

# def arrears_in_current_sal_slip(self, *args, **kwargs):
# 	all_sal_slip = frappe.db.get_all("Salary Slip", filters={"employee": self.employee, "custom_gross_arrears": [">", 0], "docstatus": ["=", "1"], "creation": ["<", frappe.utils.today()]})
# 	earned = {}
# 	deducted = {}
# 	for ss in all_sal_slip:
# 		sal_slip_doc = frappe.get_doc("Salary Slip", ss.name)
# 		for e in sal_slip_doc.earnings:
# 			if e.salary_component not in earned:
# 				earned[e.salary_component] = e.custom_arrears_difference
# 			if e.salary_component in earned:
# 				earned[e.salary_component] = earned[e.salary_component] + e.custom_arrears_difference
		
# 		for e in sal_slip_doc.deductions:
# 			if e.salary_component not in deducted:
# 				deducted[e.salary_component] = e.custom_arrears_difference
# 			if e.salary_component in deducted:
# 				deducted[e.salary_component] = deducted[e.salary_component] + e.custom_arrears_difference

# 	for e in self.earnings:
# 		if e.salary_component in earned:
# 			e.custom_arrears_difference = earned[e.salary_component]
# 	for e in self.deductions:
# 		if e.salary_component in deducted:
# 			e.custom_arrears_difference = deducted[e.salary_component]

#     ss.process_salary_based_on_working_days()

# @frappe.whitelist()
# def process_salary_based_on_working_days(self):
#     self.get_working_days_details(lwp=self.leave_without_pay)
#     self.calculate_net_pay()