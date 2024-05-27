import frappe
import cx_Oracle
from real_group.real_group.employee_map import EMPLOYEE_MAP, ACCOUNT_MAP, USER_MAP
# from real_group.real_group.account_map import ACCOUNT_MAP
# from real_group.real_group.user_map import USER_MAP

ORACLE_USER="hpuser"
ORACLE_PASSWORD="hrms@erp$test"
ORACLE_DSN="192.168.2.197/ORCLRIPL"

#----------------Employee CRUD Operation

def create_employee(doc, method):

	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOc", message=doc.as_json())			
			cur = con.cursor()
			
			check_emp_sql = f"""SELECT EMP_CODE FROM RIPLRR.EMP_MAST WHERE EMP_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_update_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.log_error(title="update query", message=sql)
				cur.execute(sql)

			else:
				sql = get_insert_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.log_error(title="Insert query", message=sql)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)
			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def update_employee(doc, method):
	frappe.log_error(message=doc.as_json(), title="update_employee_trigger")

	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOc", message=doc.as_json())			
			cur = con.cursor()
			check_emp_sql = f"""SELECT EMP_CODE FROM RIPLRR.EMP_MAST WHERE EMP_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_update_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.log_error(title="update query", message=sql)
				cur.execute(sql)

			else:
				sql = get_insert_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.log_error(title="insert query", message=sql)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)

			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def oracle_connection():
	try:
		con = cx_Oracle.connect()
		print(con.version)
		con.close()
	except Exception as e:
		print(e)
		
def get_insert_query(map, table_name, employee_code):
	employee_values = frappe.db.sql("""
        SELECT
			*,
            name,
            employee_name,
            date_of_joining,
            (SELECT custom_erp_code FROM `tabDepartment` WHERE name = department  LIMIT 1) as department,
            grade,
            (SELECT custom_erp_code FROM `tabDesignation` WHERE name = designation  LIMIT 1) as designation,
            date_of_birth,
            custom_father_name,
            custom_mother_name,
            (SELECT custom_erp_code FROM `tabCompany` WHERE name = company  LIMIT 1) as company,
            (SELECT erp_code FROM `tabDivision` WHERE name = custom_division  LIMIT 1) as custom_division,
            (SELECT custom_erp_code FROM `tabGender` WHERE name = gender LIMIT 1) as gender,
            pan_number,
			passport_number,
			bank_name,
			bank_ac_no,
            custom_esic,
			reports_to,
            relieving_date,
            reason_for_leaving,
            modified,
			creation,
			default_shift,
            blood_group,
			ifsc_code,
			custom_payroll_series,
			(SELECT username FROM `tabUser` WHERE name = owner) as user_id,
            CASE
                WHEN salary_mode = 'BANK' THEN 'B'
                WHEN salary_mode = 'CASH' THEN 'C'
                WHEN salary_mode = 'CHEQUE' THEN 'CH'
                ELSE salary_mode
            END AS salary_mode,
            CASE
                WHEN custom_skill_status = 'S - SKILLED' THEN 'S'
                WHEN custom_skill_status = 'U - UNSKILLED' THEN 'U'
                WHEN custom_skill_status = 'SEMI A - SEMI SKILLED A' THEN 'SEMI A'
                WHEN custom_skill_status = 'SEMI B - SEMI SKILLED B' THEN 'SEMI B'
                WHEN custom_skill_status = 'H - HIGH SKILLED' THEN 'H'
                ELSE custom_skill_status
            END AS custom_skill_status
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict =1)

	if not employee_values:
		return None

	employee_values = employee_values[0]

	keys = []
	values = []

	sql = ""

	# for key, value in map.items():
	# 	if value:
	# 		keys.append(key)
	# 		values.append(frappe.db.get_value("Employee", employee_code, value))


	for key, value in map.items():
		if value:
			keys.append(key)
			value_to_insert = None
			if employee_values[value]:
				value_to_insert = employee_values[value]
			if value_to_insert is None:
				values.append('')
			else:
				if 'date' in value:
					values.append(f"TO_DATE('{value_to_insert}', 'YYYY-MM-DD')")
				elif 'modified' in value:
					value_to_insert = str(value_to_insert).split(".")
					values.append(f"TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
				else:
					values.append(f"{value_to_insert}")


	sql = f"""
		INSERT INTO {table_name}
			({','.join([str(elem) for elem in keys])})
		VALUES
			({','.join([str(elem) if 'TO_DATE' in str(elem) else "'" + str(elem) + "'" for elem in values])})
	"""

	print(sql)
	return sql

def get_update_query(map, table_name, employee_code):
    employee_values = frappe.db.sql("""
        SELECT
			*,
            name,
            employee_name,
            date_of_joining,
            (SELECT custom_erp_code FROM `tabDepartment` WHERE name = department  LIMIT 1) as department,
            grade,
            (SELECT custom_erp_code FROM `tabDesignation` WHERE name = designation  LIMIT 1) as designation,
            date_of_birth,
            custom_father_name,
            custom_mother_name,
            (SELECT custom_erp_code FROM `tabCompany` WHERE name = company  LIMIT 1) as company,
            (SELECT erp_code FROM `tabDivision` WHERE name = custom_division  LIMIT 1) as custom_division,
            (SELECT custom_erp_code FROM `tabGender` WHERE name = gender LIMIT 1) as gender,
            pan_number,
			passport_number,
			bank_name,
			bank_ac_no,
            custom_esic,
			reports_to,
            relieving_date,
            reason_for_leaving,
            modified,
			creation,
			default_shift,
            blood_group,
			ifsc_code,
			custom_payroll_series,
			(SELECT username FROM `tabUser` WHERE name = owner) as user_id,
            CASE
                WHEN salary_mode = 'BANK' THEN 'B'
                WHEN salary_mode = 'CASH' THEN 'C'
                WHEN salary_mode = 'CHEQUE' THEN 'CH'
                ELSE salary_mode
            END AS salary_mode,
            CASE
                WHEN custom_skill_status = 'S - SKILLED' THEN 'S'
                WHEN custom_skill_status = 'U - UNSKILLED' THEN 'U'
                WHEN custom_skill_status = 'SEMI A - SEMI SKILLED A' THEN 'SEMI A'
                WHEN custom_skill_status = 'SEMI B - SEMI SKILLED B' THEN 'SEMI B'
                WHEN custom_skill_status = 'H - HIGH SKILLED' THEN 'H'
                ELSE custom_skill_status
            END AS custom_skill_status
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict=True)

    if not employee_values:
        return None

    employee_values = employee_values[0]

    set_clauses = []

    for key, value in map.items():
        if value:
            value_to_update = employee_values[value]
            if value_to_update is None:
                set_clauses.append(f"{key} = ''")
            else:
                if 'date' in value:
                    set_clauses.append(f"{key} = TO_DATE('{value_to_update}', 'YYYY-MM-DD')")
                elif 'modified' in value:
                    value_to_update = str(value_to_update).split(".")
                    set_clauses.append(f"{key} = TO_DATE('{value_to_update[0]}', 'YYYY-MM-DD HH24:MI:SS')")
                else:
                    set_clauses.append(f"{key} = '{value_to_update}'")

    sql = f"""
        UPDATE {table_name}
        SET
            {', '.join(set_clauses)}
        WHERE
            EMP_CODE = '{employee_code}'
    """

    print(sql)
    return sql


#----------------Account CRUD Operation


def create_account(doc, method):

	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOC", message=doc.as_json())			
			cur = con.cursor()
			
			check_emp_sql = f"""SELECT ACC_CODE FROM RIPLRR.ACC_MAST WHERE ACC_CODE = '{doc.name}'"""
			frappe.log_error(title="check_emp_sql_SWL", message=check_emp_sql)
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				frappe.log_error(title="EMP_CODE", message=str(emp_code))
				sql = get_account_update_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)

			else:
				frappe.log_error(title="EMP_CODE", message="No result found")
				sql = get_account_insert_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)

			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def update_account(doc, method):
	frappe.log_error(message=doc.as_json(), title="update_account_trigger")
	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOC", message=doc.as_json())			
			cur = con.cursor()
			
			check_emp_sql = f"""SELECT ACC_CODE FROM RIPLRR.ACC_MAST WHERE ACC_CODE = '{doc.name}'"""
			frappe.log_error(title="check_emp_sql_SWL", message=check_emp_sql)
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				frappe.log_error(title="EMP_CODE", message=str(emp_code))
				sql = get_account_update_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)

			else:
				frappe.log_error(title="EMP_CODE", message="No result found")
				sql = get_account_insert_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)

			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def get_account_insert_query(map, table_name, employee_code):
	employee_values = frappe.db.sql("""
        SELECT
            name,
            employee_name,
			654321 as user_id
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict =1)

		# temp Syntex for user id
		# (SELECT name FROM `tabUser` WHERE name = owner) as user_id


	if not employee_values:
		return None

	employee_values = employee_values[0]

	keys = []
	values = []
	for key, value in map.items():
		if value:
			keys.append(key)
			value_to_insert = employee_values[value]
			if value_to_insert is None:
				values.append('')
			else:
				values.append(f"{value_to_insert}")

	sql = f"""
		INSERT INTO {table_name}
			({','.join([str(elem) for elem in keys])})
		VALUES
			({','.join([str(elem) if 'TO_DATE' in str(elem) else "'" + str(elem) + "'" for elem in values])})
	"""
	frappe.log_error(title="Query_Bulding_Syntex", message=sql)

	print(sql)
	return sql

def get_account_update_query(map, table_name, employee_code):
    employee_values = frappe.db.sql("""
        SELECT
            name,
            employee_name,
			654321 as user_id
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict=True)

    if not employee_values:
        return None

    employee_values = employee_values[0]

    set_clauses = []

    for key, value in map.items():
        if value:
            value_to_update = employee_values[value]
            if value_to_update is None:
                set_clauses.append(f"{key} = ''")
            else:
                set_clauses.append(f"{key} = '{value_to_update}'")

    sql = f"""
        UPDATE {table_name}
        SET
            {', '.join(set_clauses)}
        WHERE
            ACC_CODE = '{employee_code}'
    """

    print(sql)
    return sql


#----------------USER CRUD Operation



def create_user(doc, method):

	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOC", message=doc.as_json())			
			cur = con.cursor()
			
			check_emp_sql = f"""SELECT USER_CODE FROM RIPLRR.USER_MAST WHERE USER_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_user_update_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)

			else:
				sql = get_user_insert_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)

			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def update_user(doc, method):
	frappe.log_error(message=doc.as_json(), title="update_account_trigger")
	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="DOC", message=doc.as_json())			
			cur = con.cursor()
			check_emp_sql = f"""SELECT USER_CODE FROM RIPLRR.USER_MAST WHERE USER_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_user_update_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)

			else:
				sql = get_user_insert_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)
				# rows = cur.fetchall()
				# print(rows)

			con.commit() #-----------------Database commit value

		except cx_Oracle.DatabaseError as er:
			frappe.log_error(title="Oracle Query Error", message=er)
			frappe.throw('Oracle Query Error:', str(er))
			con.rollback()

		except Exception as er:
			frappe.log_error(title="Oracle Exception", message=er)
			frappe.throw('Oracle Exception:', str(er))
			con.rollback()

		finally:
			if cur:
				cur.close()

	finally:
		if con:
			con.close()

def get_user_insert_query(map, table_name, employee_code):
	employee_values = frappe.db.sql("""
        SELECT
			*,
            name,
            employee_name,
			'DF39CA1D0B6BBAF9' as password,
			9 as user_level,
            25 as passwd_reset_days,
            (SELECT custom_erp_code FROM `tabDepartment` WHERE name = department  LIMIT 1) as department,
            (SELECT custom_erp_code FROM `tabCompany` WHERE name = company  LIMIT 1) as company,
            (SELECT erp_code FROM `tabDivision` WHERE name = custom_division  LIMIT 1) as custom_division,
            (SELECT username FROM `tabUser` WHERE name = owner) as created_by
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict =1)

		# temp Syntex for user id
		# (SELECT name FROM `tabUser` WHERE name = owner) as user_id


	if not employee_values:
		return None

	employee_values = employee_values[0]

	keys = []
	values = []
	for key, value in map.items():
		if value:
			keys.append(key)
			value_to_insert = employee_values[value]
			if value_to_insert is None:
				values.append('')
			else:
				values.append(f"{value_to_insert}")

	formatted_values = []
	for elem in values:
		elem_str = str(elem)
		if 'TO_DATE' in elem_str:
			formatted_values.append(elem_str)
		elif 'passwd_reset_days' in elem_str or 'user_level' in elem_str:
			formatted_values.append(int(elem))
		else:
			formatted_values.append("'" + elem_str + "'")
			
	sql = f"""
		INSERT INTO {table_name}
			({','.join([str(elem) for elem in keys])})
		VALUES
			({','.join(formatted_values)})
	"""
	frappe.log_error(title="Query_Bulding_Syntex", message=sql)

	print(sql)
	return sql

def get_user_update_query(map, table_name, employee_code):
    employee_values = frappe.db.sql("""
        SELECT
            *,
            name,
            employee_name,
			'DF39CA1D0B6BBAF9' as password,
			9 as user_level,
            25 as passwd_reset_days,
            (SELECT custom_erp_code FROM `tabDepartment` WHERE name = department  LIMIT 1) as department,
            (SELECT custom_erp_code FROM `tabCompany` WHERE name = company  LIMIT 1) as company,
            (SELECT erp_code FROM `tabDivision` WHERE name = custom_division  LIMIT 1) as custom_division,
            (SELECT username FROM `tabUser` WHERE name = owner) as user_id
        FROM
            `tabEmployee`
        WHERE
            name = %s
    """, (employee_code), as_dict=True)

    if not employee_values:
        return None

    employee_values = employee_values[0]

    set_clauses = []

    for key, value in map.items():
        if value:   
            value_to_update = employee_values[value]
            if value_to_update is None:
                set_clauses.append(f"{key} = ''")

            elif 'TO_DATE' in str(value):
                set_clauses.append(f"{key} = {value_to_update}")

            elif 'passwd_reset_days' in str(value):
                set_clauses.append(f"{key} = {int(value_to_update)}")

            elif 'user_level' in str(value):
                set_clauses.append(f"{key} = {int(value_to_update)}")

            elif isinstance(value, str) and 'DATE' in key.upper():
                set_clauses.append(f"{key} = TIMESTAMP '{value_to_update}'")

            else:
                set_clauses.append(f"{key} = '{value_to_update}'")

    frappe.log_error(title="set_clauses", message=set_clauses)

    sql = f"""
        UPDATE {table_name}
        SET
            {', '.join(set_clauses)}
        WHERE
            USER_CODE = '{employee_code}'
    """

    print(sql)
    return sql





