import datetime

import frappe
import pyqrcode
from frappe.utils import add_to_date, flt, get_first_day, getdate, today


def get_qr_code(value, scale):
    qr = pyqrcode.create(value).png_as_base64_str(scale=scale, quiet_zone=1)
    return f'<img src="data:image/png;base64,{qr}" class="qrcode">'


@frappe.whitelist()
def employee_advance_details(today, employee):
    today = get_first_day(add_to_date(today, months=-1))
    last_six_month_date = add_to_date(today, months=-6)
    start_date = get_first_day(last_six_month_date)

    last_six_months = [(today - datetime.timedelta(days=i * 30)).strftime("%B") for i in range(6)][::-1]

    monthly_data = {month: {"payment_days": 0, "absent_days": 0, "gross_pay": 0} for month in last_six_months}

    salary_slips = frappe.db.get_list(
        "Salary Slip",
        filters=[
            ["start_date", "between", [start_date, today]],
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 1],
        ],
    )

    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

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
        amount = frappe.utils.fmt_money(monthly_data[month]["gross_pay"], currency="INR")
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

    x = frappe.db.sql(
        """
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
        """,
        (employee, today),
        as_dict=1,
    )

    employee_adv = {}
    total_installments = 1
    remaining_installments = 1

    for rec in x:
        posting_date_str = str(rec.get("posting_date"))
        if posting_date_str in employee_adv:
            employee_adv[posting_date_str].get("Result").append(rec)
            employee_adv[posting_date_str]["total_installments"] = (
                employee_adv[posting_date_str]["total_installments"] + 1
            )
            if frappe.utils.getdate(today) < rec.get("payroll_date"):
                employee_adv[posting_date_str]["remaining_installments"] = (
                    employee_adv[posting_date_str]["remaining_installments"] + 1
                )
        else:
            if frappe.utils.getdate(today) < rec.get("payroll_date"):
                remaining_installments = 0
            employee_adv[posting_date_str] = {
                "Result": [rec],
                "total_installments": total_installments,
                "remaining_installments": remaining_installments,
            }

    html = """
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
            <tbody>"""
    for res in employee_adv:
        amount = frappe.utils.fmt_money(employee_adv[res].get("Result")[0].advance_amount, currency="INR")
        html = (
            html
            + f"""
                <tr>
                    <td>{employee_adv[res].get("Result")[0].emp_adv}</td>
                    <td>{res}</td>
                    <td>{amount}</td>
                    <td>{employee_adv[res].get("total_installments")}</td>
                    <td>{employee_adv[res].get("remaining_installments")}</td>
                </tr>"""
        )

    html = (
        html
        + """
            </tbody>
        </table> """
    )

    return html


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employees(doctype, txt, searchfield, start, page_len, filters):
    values = {"txt": txt}

    return frappe.db.sql(
        """SELECT name, employee_name FROM `tabEmployee` WHERE status = 'Active' """, values=values, as_dict=0
    )


@frappe.whitelist()
def get_salary_contributions(employee: str, salary_structure: str):
    """
    Returns PF and ESIC contributions (Employee + Employer side).
    Dynamically evaluates PF formula from Salary Detail (no hardcoding).
    """

    result = {
        "pf_employee_monthly": 0,
        "pf_employee_yearly": 0,
        "esic_employee_monthly": 0,
        "esic_employee_yearly": 0,
        "pf_employer_monthly": 0,
        "pf_employer_yearly": 0,
        "esic_employer_monthly": 0,
        "esic_employer_yearly": 0,
    }

    if not employee or not salary_structure:
        return result

    emp = frappe.get_doc("Employee", employee)
    ss = frappe.get_doc("Salary Structure", salary_structure)

    # --- Get Basic ---
    basic_row = next((e for e in ss.earnings if e.salary_component == "Basic"), None)
    basic_amount = flt(basic_row.amount) if basic_row else 0

    # --- Fetch PF formula from Salary Detail ---
    pf_row = frappe.db.get_value(
        "Salary Detail",
        {"parent": salary_structure, "salary_component": "Provident Fund"},
        ["formula"],
        as_dict=True,
    )

    pf_formula = (pf_row["formula"] or "").strip() if pf_row else ""

    pf_employee = pf_employer = 0

    if emp.custom_pf_number or emp.provident_fund_account:
        if pf_formula:
            try:
                # Debug log to confirm formula text and value
                frappe.logger().info(f"Evaluating PF formula for {salary_structure}: {pf_formula}, B={basic_amount}")

                # Prepare environment for safe evaluation
                local_vars = {"B": basic_amount}

                # Evaluate formula safely (e.g. ((B * 12) / 100) if B <= 15000 else 1800)
                pf_value = eval(pf_formula, {"__builtins__": {}}, local_vars)

                # If eval works and returns number
                if pf_value is not None:
                    pf_employee = round(flt(pf_value))
                    pf_employer = round(flt(pf_value))
                else:
                    # Fallback if eval returns None
                    pf_employee = round(basic_amount * 0.12)
                    pf_employer = round(basic_amount * 0.12)

            except Exception as e:
                frappe.log_error(
                    f"PF formula evaluation failed for {salary_structure}\nFormula: {pf_formula}\nError: {e}",
                    "PF Formula Error",
                )
                pf_employee = round(basic_amount * 0.12)
                pf_employer = round(basic_amount * 0.12)
        else:
            # No formula defined
            pf_employee = round(basic_amount * 0.12)
            pf_employer = round(basic_amount * 0.12)

    # --- ESIC logic ---
    gross_monthly = flt(ss.total_earning)
    esic_employee = esic_employer = 0

    if gross_monthly <= 21000:
        esic_employee = round(gross_monthly * 0.0075)
        esic_employer = round(gross_monthly * 0.0325)
    elif (
        getattr(emp, "custom_previous_base", 0) <= 21000
        and getattr(emp, "custom_esi_exit_date", None)
        and getdate(today()) <= getdate(emp.custom_esi_exit_date)
    ):
        esic_employee = round(gross_monthly * 0.0075)
        esic_employer = round(gross_monthly * 0.0325)

    # --- Return combined data ---
    result.update(
        {
            "pf_employee_monthly": pf_employee,
            "pf_employee_yearly": pf_employee * 12,
            "esic_employee_monthly": esic_employee,
            "esic_employee_yearly": esic_employee * 12,
            "pf_employer_monthly": pf_employer,
            "pf_employer_yearly": pf_employer * 12,
            "esic_employer_monthly": esic_employer,
            "esic_employer_yearly": esic_employer * 12,
        }
    )

    return result
