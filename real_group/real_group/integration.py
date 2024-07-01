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


			#-------------------------------------------------------Employee Creation CRUD
			check_emp_sql = f"""SELECT EMP_CODE FROM RIPLRR.EMP_MAST WHERE EMP_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_update_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.throw("Employee ID present in oracle, clean it first!!")
				frappe.log_error(title="update query for employee", message=sql)
				cur.execute(sql)

			else:
				sql = get_insert_query(EMPLOYEE_MAP, 'RIPLRR.EMP_MAST', doc.name)
				frappe.log_error(title="Insert query for employee", message=sql)
				cur.execute(sql)

			#-------------------------------------------------------Account Creation CRUD

			check_acc_sql = f"""SELECT ACC_CODE FROM RIPLRR.ACC_MAST WHERE ACC_CODE = '{doc.name}'"""
			frappe.log_error(title="check_acc_sql_SWL", message=check_acc_sql)
			my_count = cur.execute(check_acc_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				frappe.log_error(title="EMP_CODE", message=str(emp_code))
				frappe.throw("Account ID present in oracle, clean it first!!")
				sql = get_account_update_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)

			else:
				frappe.log_error(title="EMP_CODE", message="No result found")
				sql = get_account_insert_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="SWL", message=sql)
				cur.execute(sql)


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

			#--------------------------------------Account Updataion CRUD

			check_acc_code_sql = f"""SELECT ACC_CODE FROM RIPLRR.ACC_MAST WHERE ACC_CODE = '{doc.name}'"""
			my_count = cur.execute(check_acc_code_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				sql = get_account_update_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="account Update Query", message=sql)
				cur.execute(sql)

			else:
				frappe.log_error(title="EMP_CODE", message="No result found")
				sql = get_account_insert_query(ACCOUNT_MAP, 'RIPLRR.ACC_MAST', doc.name)
				frappe.log_error(title="account insert Query", message=sql)
				cur.execute(sql)

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
			name,
			employee_name,
			date_of_joining,
			(SELECT custom_erp_code FROM `tabDepartment` WHERE name = e.department  LIMIT 1) as department,
			grade,
			(SELECT custom_erp_code FROM `tabDesignation` WHERE name = e.designation  LIMIT 1) as designation,
			date_of_birth,
			custom_father_name,
			custom_mother_name,
			custom_off_days,
			(SELECT custom_erp_code FROM `tabCompany` WHERE name = e.company  LIMIT 1) as company,
			(SELECT erp_code FROM `tabDivision` WHERE name = e.custom_division  LIMIT 1) as custom_division,
			(SELECT custom_erp_code FROM `tabGender` WHERE name = e.gender LIMIT 1) as gender,
			(SELECT custom_erp_itax_category FROM `tabGender` WHERE name = e.gender LIMIT 1) as custom_itax_category,
			pan_number,
			passport_number,
			(SELECT custom_erp_code FROM `tabBank` WHERE name = e.bank_name LIMIT 1) as bank_name,
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
			cell_number,
			current_address,
			custom_payroll_series,
			custom_aadhar_number,
			permanent_address,
			custom_emergency_address,
			emergency_phone_number,
			person_to_be_contacted,
			custom_permanent_pin_code,
			custom_permanent_country,
			custom_current_country,
			custom_current_pin_code,
			date_of_retirement,
			date_of_joining,
			(SELECT username FROM `tabUser` WHERE name = e.owner) as user_id,
			(SELECT erp_code FROM `tabSalary Mode` WHERE name = e.salary_mode LIMIT 1) as salary_mode,
			(SELECT erp_code FROM `tabSkill Status` WHERE name = e.custom_skill_status LIMIT 1) as custom_skill_status,
			(SELECT erp_code FROM `tabReligion` WHERE name = e.custom_religion LIMIT 1) as custom_religion,
			(SELECT erp_code FROM `tabWage Basis` WHERE name = e.custom_wage_basis LIMIT 1) as custom_wage_basis,
			custom_permanent_city,
			custom_permanent_district,
			(SELECT erp_code FROM `tabState` WHERE name = e.custom_permanent_state LIMIT 1) as custom_permanent_state,
			custom_current_city,
			custom_current_district,
			(SELECT erp_code FROM `tabState` WHERE name = e.custom_current_state LIMIT 1) as custom_current_state,
			(SELECT erp_code FROM `tabEmployee Category` WHERE name = e.custom_emp_category LIMIT 1) as custom_emp_category,
			(SELECT erp_code FROM `tabPayroll Series` WHERE name = e.custom_payroll_series LIMIT 1) as custom_payroll_series
		FROM
			`tabEmployee` e
		WHERE
			name = %s
	""", (employee_code), as_dict =1)

	if not employee_values:
		return None

	employee_values = employee_values[0]

	keys = []
	values = []

	sql = ""

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
			name,
			employee_name,
			date_of_joining,
			(SELECT custom_erp_code FROM `tabDepartment` WHERE name = e.department  LIMIT 1) as department,
			grade,
			(SELECT custom_erp_code FROM `tabDesignation` WHERE name = e.designation  LIMIT 1) as designation,
			date_of_birth,
			custom_father_name,
			custom_mother_name,
			custom_off_days,
			(SELECT custom_erp_code FROM `tabCompany` WHERE name = e.company  LIMIT 1) as company,
			(SELECT erp_code FROM `tabDivision` WHERE name = e.custom_division  LIMIT 1) as custom_division,
			(SELECT custom_erp_code FROM `tabGender` WHERE name = e.gender LIMIT 1) as gender,
			(SELECT custom_erp_itax_category FROM `tabGender` WHERE name = e.gender LIMIT 1) as custom_itax_category,
			pan_number,
			passport_number,
			(SELECT custom_erp_code FROM `tabBank` WHERE name = e.bank_name LIMIT 1) as bank_name,
			bank_ac_no,
			current_address,
			custom_esic,
			reports_to,
			relieving_date,
			reason_for_leaving,
			modified,
			creation,
			default_shift,
			blood_group,
			ifsc_code,
			cell_number,
			custom_payroll_series,
			custom_aadhar_number,
			permanent_address,
			custom_emergency_address,
			emergency_phone_number,
			person_to_be_contacted,
			custom_permanent_pin_code,
			custom_permanent_country,
			custom_current_country,
			custom_current_pin_code,
			date_of_retirement,
			date_of_joining,
			(SELECT username FROM `tabUser` WHERE name = e.owner) as user_id,
			(SELECT erp_code FROM `tabSalary Mode` WHERE name = e.salary_mode LIMIT 1) as salary_mode,
			(SELECT erp_code FROM `tabSkill Status` WHERE name = e.custom_skill_status LIMIT 1) as custom_skill_status,
			(SELECT erp_code FROM `tabReligion` WHERE name = e.custom_religion LIMIT 1) as custom_religion,
			(SELECT erp_code FROM `tabWage Basis` WHERE name = e.custom_wage_basis LIMIT 1) as custom_wage_basis,
			custom_permanent_city,
			custom_permanent_district,
			(SELECT erp_code FROM `tabState` WHERE name = e.custom_permanent_state LIMIT 1) as custom_permanent_state,
			custom_current_city,
			custom_current_district,
			(SELECT erp_code FROM `tabState` WHERE name = e.custom_current_state LIMIT 1) as custom_current_state,
			(SELECT erp_code FROM `tabEmployee Category` WHERE name = e.custom_emp_category LIMIT 1) as custom_emp_category,
			(SELECT erp_code FROM `tabPayroll Series` WHERE name = e.custom_payroll_series LIMIT 1) as custom_payroll_series
		FROM
			`tabEmployee` e
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
				if  value == 'name':
					continue # Skip to the next iteration if 'name' is found in value
				elif 'date' in value:
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

#-------------------------Account CRUD Operation Query

def get_account_insert_query(map, table_name, employee_code):
	employee_values = frappe.db.sql("""
		SELECT
			name,
			employee_name,
			(SELECT username FROM `tabUser` WHERE name = owner) as user_id
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
	# frappe.log_error(title="Query_Bulding_Syntex", message=sql)

	print(sql)
	return sql

def get_account_update_query(map, table_name, employee_code):
	employee_values = frappe.db.sql("""
		SELECT
			name,
			employee_name,
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
			elif key == 'name':
					continue
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
			frappe.log_error(title="User Document", message=doc.as_json())			
			cur = con.cursor()
			
			check_emp_sql = f"""SELECT USER_CODE FROM RIPLRR.USER_MAST WHERE USER_CODE = '{doc.name}'"""
			my_count = cur.execute(check_emp_sql)
			result = cur.fetchall() 
			if result:
				emp_code = result[0]
				frappe.log_error(title="User_CODE", message=str(emp_code))
				frappe.throw(f"User ID {emp_code} present in oracle, clean it first!!")
				sql = get_user_update_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="User Update Query", message=sql)
				cur.execute(sql)

			else:
				sql = get_user_insert_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="User Insert Query", message=sql)
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
				frappe.log_error(title="User Update Query", message=sql)
				cur.execute(sql)

			else:
				sql = get_user_insert_query(USER_MAP, 'RIPLRR.USER_MAST', doc.name)
				frappe.log_error(title="User Insert Query", message=sql)
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

def get_user_insert_query(map, table_name, user_code):
	employee_values = frappe.db.sql("""
		SELECT
			u.name as name,
			u.full_name as full_name,
			9 as user_level,
			(SELECT custom_erp_code FROM `tabDepartment` WHERE name = e.department  LIMIT 1) as department,
			(SELECT custom_erp_code FROM `tabCompany` WHERE name = e.company  LIMIT 1) as company,
			(SELECT erp_code FROM `tabDivision` WHERE name = e.custom_division  LIMIT 1) as custom_division,
			e.name as emp_code,
			90 as passwd_reset_days,
			(SELECT username FROM `tabUser` WHERE name = owner) as created_by,
			u.creation,
			u.modified
		FROM
			`tabUser` u
		LEFT JOIN
			`tabEmployee` e ON e.name = u.name
		WHERE
			u.name = %s
	""", (user_code), as_dict =1)

		# temp Syntex for user id
		# (SELECT name`` FROM `tabUser` WHERE name = owner) as user_id


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
	frappe.log_error(title="Query_Bulding_Syntax", message=sql)

	print(sql)
	return sql

def get_user_update_query(map, table_name, user_code):
	employee_values = frappe.db.sql("""
		SELECT
			u.name as name,
			u.full_name as full_name,
			9 as user_level,
			(SELECT custom_erp_code FROM `tabDepartment` WHERE name = e.department  LIMIT 1) as department,
			(SELECT custom_erp_code FROM `tabCompany` WHERE name = e.company  LIMIT 1) as company,
			(SELECT erp_code FROM `tabDivision` WHERE name = e.custom_division  LIMIT 1) as custom_division,
			e.name as emp_code,
			90 as passwd_reset_days,
			(SELECT username FROM `tabUser` WHERE name = owner) as created_by,
			u.creation,
			u.modified
		FROM
			`tabUser` u
		LEFT JOIN
			`tabEmployee` e ON e.name = u.name
		WHERE
			u.name = %s
	""", (user_code), as_dict=True)

	if not employee_values:
		return None

	employee_values = employee_values[0]

	set_clauses = []

	for key, value in map.items():
		if value:   
			value_to_update = employee_values[value]
			if value_to_update is None:
				set_clauses.append(f"{key} = ''")

			elif value_to_update == 'name':
					continue

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
			USER_CODE = '{user_code}'
	"""

	frappe.log_error('sql', sql)
	return sql





