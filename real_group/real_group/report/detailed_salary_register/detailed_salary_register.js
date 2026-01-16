// Copyright (c) 2026, Real Group and contributors
// For license information, please see license.txt

function get_years() {
	const currentYear = new Date().getFullYear();
	const pastYears = 5;
	const futureYears = 0;

	const startYear = currentYear - pastYears;
	const endYear = currentYear + futureYears;

	return Array.from({ length: endYear - startYear + 1 }, (_, i) => startYear + i);
}

const years = get_years();

frappe.query_reports["Detailed Salary Register"] = {
	filters: [
		{
			fieldname: "company",
			label: "Company",
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			on_change: function () {
				frappe.query_report.set_filter_value("employee", null);
			},
		},
		{
			fieldname: "branch",
			label: "Branch",
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "division",
			label: "Division",
			fieldtype: "Link",
			options: "Division",
		},
		{
			fieldname: "department",
			label: "Department",
			fieldtype: "Link",
			options: "Department",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				if (!company) {
					frappe.throw(__("Please select a company first"));
				}
				return { filters: [["Department", "company", "=", company]] };
			},
		},
		{
			fieldname: "employee",
			label: "Employee",
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				if (!company) {
					frappe.throw(__("Please select a company first"));
				}
				return { filters: [["Employee", "company", "=", company]] };
			},
		},
		{
			fieldname: "month",
			label: "Month",
			fieldtype: "Select",
			options: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
			reqd: 1,
		},
		{
			fieldname: "year",
			label: "Year",
			fieldtype: "Select",
			options: years,
			reqd: 1,
		},
	],
};
