import frappe
from frappe.utils import add_to_date, get_first_day, today
from frappe.twofactor import get_qr_svg_code
import pyqrcode
import datetime

def get_qr_code(value, scale):
    qr = pyqrcode.create(value).png_as_base64_str(scale=scale, quiet_zone=1)
    return f'<img src="data:image/png;base64,{ qr }" class="qrcode">'


@frappe.whitelist()
def employee_advance_details(today, employee):

    today = get_first_day(add_to_date(today, months = -1))
    last_six_month_date = add_to_date(today, months = -6)
    start_date = get_first_day(last_six_month_date)

    last_six_months = [(today - datetime.timedelta(days=i*30)).strftime('%B') for i in range(6)][::-1]

    monthly_data = {month: {"payment_days": 0, "absent_days": 0, "gross_pay": 0} for month in last_six_months}

    salary_slips = frappe.db.get_list('Salary Slip', filters=[
                    ['start_date', 'between', [start_date, today]],
                    ["Salary Slip","employee","=", employee],
                    ["Salary Slip","docstatus","=", 1]
                    ])

    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    for rec in salary_slips:
        ss = frappe.get_doc("Salary Slip", rec.name)
        month_name = months[ss.start_date.month - 1]
        if month_name in monthly_data:
            monthly_data[month_name] = {
                "payment_days": ss.payment_days,
                "absent_days": ss.absent_days,
                "gross_pay": ss.gross_pay,
            }
    
    months = list(monthly_data.keys())

    html_table = """
        <table class="table table-bordered text-center">
            <thead>
                <tr>
                    <th style='width:20%'>&nbsp;</th>"""

    # Adding months to the table header
    for month in months:
        html_table += f"<th>{month}</th>"

    html_table += """
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="text-center" >Payment Days</td>"""

    # Adding payment days to the table
    for month in months:
        html_table += f"<td>{monthly_data[month]['payment_days']}</td>"

    html_table += """
                </tr>
                <tr>
                    <td class="text-center" >Absent Days</td>"""

    # Adding absent days to the table
    for month in months:
        html_table += f"<td>{monthly_data[month]['absent_days']}</td>"

    html_table += """
                </tr>
                <tr>
                    <td class="text-center" >Gross Pay</td>"""

    # Adding gross pay to the table
    for month in months:
        amount = frappe.utils.fmt_money(monthly_data[month]['gross_pay'] , currency="INR")
        html_table += f"<td>{amount}</td>"

    html_table += """
                </tr>
            </tbody>
        </table>
    """

    return html_table




@frappe.whitelist()
def existing_loan_summary(today, employee):
    # today = '2024-11-11'
    # employee = '12131'

    x = frappe.db.sql("""
        SELECT
            ea.employee,
            ea.posting_date,
            ea.advance_amount,
            ea.name as emp_adv,
            adds.name as add_s_name,
            adds.payroll_date 
        FROM
            `tabEmployee Advance` as ea
        LEFT JOIN
            `tabAdditional Salary` as adds ON adds.ref_docname = ea.name
        WHERE
            ea.employee = %s
            AND ea.docstatus = 1
            AND adds.docstatus = 1
            AND ea.posting_date != %s
        ORDER BY
            adds.payroll_date
        """,(employee, today), as_dict=1)
        
    employee_adv = {}
    total_installments = 1
    remaining_installments = 1

    for rec in x:
        posting_date_str = str(rec.get("posting_date"))
        if posting_date_str in employee_adv:
            employee_adv[posting_date_str].get("Result").append(rec)
            employee_adv[posting_date_str]["total_installments"] = employee_adv[posting_date_str]["total_installments"] + 1 
            if frappe.utils.getdate(today) < rec.get("payroll_date"):
                employee_adv[posting_date_str]["remaining_installments"] = employee_adv[posting_date_str]["remaining_installments"] + 1 
        else:
            if frappe.utils.getdate(today) < rec.get("payroll_date"):
                remaining_installments = 0
            employee_adv[posting_date_str] = {"Result": [rec], "total_installments": total_installments, "remaining_installments":remaining_installments}

    html = '''
        <table class="table table-bordered text-center" >
            <thead>
                <tr>
                    <td> Employee Advance </td>
                    <td> Date </td>
                    <td> Total Amount </td>
                    <td> Total Installment </td>
                    <td> Remaining Installment </td>
                </tr>
            </thead>
            <tbody>'''
    for res in employee_adv:
        amount = frappe.utils.fmt_money(employee_adv[res].get("Result")[0].advance_amount, currency="INR")
        html = html + f''' 
                <tr>
                    <td>{employee_adv[res].get("Result")[0].emp_adv}</td>
                    <td>{res}</td>
                    <td>{amount}</td>
                    <td>{employee_adv[res].get("total_installments")}</td>
                    <td>{employee_adv[res].get("remaining_installments")}</td>
                </tr>'''

    html = html + '''
            </tbody>
        </table> '''

    return html


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employees(doctype, txt, searchfield, start, page_len, filters):
	employee = filters.get("employee")
	values = {"txt":txt}

	return frappe.db.sql("""SELECT name, employee_name FROM `tabEmployee` WHERE status = 'Active' """, values=values, as_dict = 0)