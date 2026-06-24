import frappe
from frappe.utils import ceil, flt, floor, getdate
from hrms.payroll.utils import sanitize_expression


def before_save(doc, method=None):
    values = get_salary_structure_assignment_values(doc.salary_structure)
    doc.custom_basic_pay = values.get("basic_pay")
    doc.base = values.get("base")


@frappe.whitelist()
def get_salary_structure_assignment_values(salary_structure):
    return {
        "basic_pay": get_salary_structure_basic_pay(salary_structure),
        "base": get_salary_structure_total_earning(salary_structure),
    }


@frappe.whitelist()
def get_salary_structure_basic_pay(salary_structure):
    if not salary_structure:
        return 0

    basic_pay = frappe.db.get_value(
        "Salary Detail",
        filters={
            "parent": salary_structure,
            "parenttype": "Salary Structure",
            "parentfield": "earnings",
            "salary_component": "Basic",
            "abbr": "B",
        },
        fieldname="amount",
        order_by="idx asc",
    )

    return flt(basic_pay)


def get_salary_structure_total_earning(salary_structure):
    if not salary_structure:
        return 0

    return flt(frappe.db.get_value("Salary Structure", salary_structure, "total_earning"))


@frappe.whitelist()
def get_projected_breakup(salary_structure_assignment):
    if not salary_structure_assignment:
        return _empty_projected_breakup()

    doc = frappe.get_doc("Salary Structure Assignment", salary_structure_assignment)
    if not doc.salary_structure:
        return _empty_projected_breakup()

    salary_structure = frappe.get_doc("Salary Structure", doc.salary_structure)
    employee = frappe.get_cached_doc("Employee", doc.employee).as_dict() if doc.employee else {}
    data = _get_formula_context(doc, salary_structure, employee)

    earnings = _get_projected_rows(salary_structure.earnings, data)
    deductions = _get_projected_rows(salary_structure.deductions, data)

    total_earnings = sum(flt(row.amount) for row in earnings)
    total_deductions = sum(flt(row.amount) for row in deductions)
    pf_employer_contribution = _get_pf_employer_contribution(earnings, deductions)
    esic_employer_contribution = _get_esic_employer_contribution(earnings, deductions)
    bonus_exgratia = _get_bonus_exgratia(doc, employee, earnings)

    return {
        "earnings": earnings,
        "deductions": deductions,
        "total_earnings": total_earnings,
        "total_earnings_yearly": total_earnings * 12,
        "total_deductions": total_deductions,
        "total_deductions_yearly": total_deductions * 12,
        "net_payable": total_earnings - total_deductions,
        "net_payable_yearly": (total_earnings - total_deductions) * 12,
        "pf_employer_contribution": pf_employer_contribution,
        "pf_employer_contribution_yearly": pf_employer_contribution * 12,
        "esic_employer_contribution": esic_employer_contribution,
        "esic_employer_contribution_yearly": esic_employer_contribution * 12,
        "bonus_exgratia": bonus_exgratia,
        "bonus_exgratia_yearly": bonus_exgratia * 12,
    }


def _empty_projected_breakup():
    return {
        "earnings": [],
        "deductions": [],
        "total_earnings": 0,
        "total_earnings_yearly": 0,
        "total_deductions": 0,
        "total_deductions_yearly": 0,
        "net_payable": 0,
        "net_payable_yearly": 0,
        "pf_employer_contribution": 0,
        "pf_employer_contribution_yearly": 0,
        "esic_employer_contribution": 0,
        "esic_employer_contribution_yearly": 0,
        "bonus_exgratia": 0,
        "bonus_exgratia_yearly": 0,
    }


def _get_pf_employer_contribution(earnings, deductions):
    employee_pf = _get_component_amount(deductions, salary_component="Provident Fund", abbr="PF")
    basic = _get_component_amount(earnings, salary_component="Basic", abbr="B")

    if employee_pf <= 0 or basic <= 0:
        return 0

    pf_basic_limit = flt(frappe.db.get_single_value("Real Group Settings", "pf_basic_limit"))
    pf_base = min(basic, pf_basic_limit) if pf_basic_limit else basic

    return round(pf_base * 0.13)


def _get_esic_employer_contribution(earnings, deductions):
    employee_esic = _get_component_amount(
        deductions, salary_component="Employee State Insurance", abbr="SI"
    )
    basic = _get_component_amount(earnings, salary_component="Basic", abbr="B")

    if employee_esic <= 0 or basic <= 0:
        return 0

    esic_deduction_limit = flt(
        frappe.db.get_single_value("Real Group Settings", "esic_deduction_limit")
    )
    esic_base = min(basic, esic_deduction_limit) if esic_deduction_limit else basic

    return round(esic_base * 0.0325)


def _get_bonus_exgratia(doc, employee, earnings):
    grade = doc.get("grade") or (employee or {}).get("grade")
    basic = _get_component_amount(earnings, salary_component="Basic", abbr="B")

    if not grade or basic <= 0:
        return 0

    is_bonus_applicable, bonus_percentage = frappe.db.get_value(
        "Employee Grade",
        grade,
        ["custom_is_bonus_applicable", "custom_bonus_percentage"],
    ) or (0, 0)

    if not is_bonus_applicable:
        return 0

    return round(basic * flt(bonus_percentage) / 100)


def _get_component_amount(rows, salary_component=None, abbr=None):
    for row in rows:
        if (salary_component and row.salary_component == salary_component) or (abbr and row.abbr == abbr):
            return flt(row.amount)

    return 0


def _get_formula_context(doc, salary_structure, employee):
    data = frappe._dict()
    data.update(doc.as_dict())
    data.update(employee or {})

    data.start_date = doc.from_date
    data.end_date = doc.get("custom_esi_exit_date") or doc.from_date

    for abbr in frappe.get_all("Salary Component", pluck="salary_component_abbr"):
        data.setdefault(abbr, 0)

    # Direct component amounts are available before formulas are evaluated.
    for table in (salary_structure.earnings, salary_structure.deductions):
        for row in table:
            if row.abbr and not row.amount_based_on_formula:
                data[row.abbr] = flt(row.amount)

    return data


def _get_projected_rows(rows, data):
    projected_rows = []

    for row in rows:
        amount = _evaluate_salary_detail(row, data)
        if row.abbr:
            data[row.abbr] = amount

        projected_rows.append(
            frappe._dict(
                {
                    "salary_component": row.salary_component,
                    "abbr": row.abbr,
                    "amount": amount,
                    "yearly_amount": amount * 12,
                    "amount_based_on_formula": row.amount_based_on_formula,
                    "formula": row.formula,
                    "condition": row.condition,
                }
            )
        )

    return projected_rows


def _evaluate_salary_detail(row, data):
    if not _condition_matches(row, data):
        return 0

    amount = row.amount
    if row.amount_based_on_formula:
        formula = sanitize_expression(row.formula)
        if not formula:
            return 0

        amount = frappe.safe_eval(formula, _get_formula_globals(), data)

    return flt(amount, row.precision("amount"))


def _condition_matches(row, data):
    condition = sanitize_expression(row.condition)
    if not condition:
        return True

    return bool(frappe.safe_eval(condition, _get_formula_globals(), data))


def _get_formula_globals():
    return {
        "__builtins__": {},
        "int": int,
        "float": float,
        "round": round,
        "ceil": ceil,
        "floor": floor,
        "getdate": getdate,
    }
