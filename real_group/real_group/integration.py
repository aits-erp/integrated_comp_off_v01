import frappe
from frappe.utils.password import  get_decrypted_password
import cx_Oracle
import json
from datetime import datetime
from real_group.real_group.employee_map import EMPLOYEE_MAP, ACCOUNT_MAP, USER_MAP, SALARY_STRUCTURE_RATE_MAST, SALARY_SLIP_SALARY_TRANS, ATTENDANCE_BALANCE
# from real_group.real_group.account_map import ACCOUNT_MAP
# from real_group.real_group.user_map import USER_MAP


ORACLE_USER="hpuser"
ORACLE_PASSWORD="hrms@erp$test"
ORACLE_DSN="192.168.2.197/ORCLRIPL"

#----------------Oracle Connection

def oracle_connection():
	try:
		con = cx_Oracle.connect()
		print(con.version)
		con.close()
	except Exception as e:
		print(e)

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
			frappe.log_error(title="user new DOC", message=doc.as_json())			
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

	user_default_pass = f'{user_code}@123' 
	user_values = frappe.db.sql("""
		SELECT
			u.name as name,
			u.full_name as full_name,
			%s as password,
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
	""", (user_default_pass,user_code), as_dict =1)

		# temp Syntex for user id
		# (SELECT name`` FROM `tabUser` WHERE name = owner) as user_id


	if not user_values:
		return None

	user_values = user_values[0]

	keys = []
	values = []
	for key, value in map.items():
		if value:
			keys.append(key)
			value_to_insert = user_values[value]
			if value_to_insert is None:
				values.append('')
			else:
				if 'creation' in value:
					value_to_insert = str(value_to_insert).split(".")
					values.append(f"TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
				elif 'modified' in value:
					value_to_insert = str(value_to_insert).split(".")
					values.append(f"TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
				else:
					values.append(f"{value_to_insert}")

	formatted_values = []
	for elem in values:
		elem_str = str(elem)
		if 'TO_DATE' in elem_str:
			formatted_values.append(elem_str)
		elif 'password' in str(value):
				set_clauses.append(f"{key} = (SELECT RIPLRR.LHS_UTILITY.GET_ENCRYPT('{value_to_update}') FROM DUAL)")
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

	# print(sql)
	return sql

def get_user_update_query(map, table_name, user_code):
	user_pass = frappe.db.get_single_value('Virtual Password', 'virtual_pass')
	# frappe.throw(str(user_pass))
	
	
	user_values = frappe.db.sql("""
		SELECT
			u.name as name,
			u.full_name as full_name,
			%s as password,
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
	""", (user_pass, user_code), as_dict=True)

	if not user_values:
		return None

	frappe.db.set_value("Virtual Password", "Virtual Password", "virtual_pass", "" )

	user_values = user_values[0]

	set_clauses = []

	for key, value in map.items():
		if value:   
			value_to_update = user_values[value]
			if value_to_update is None:
				set_clauses.append(f"{key} = ''")

			elif value_to_update == 'name':
					continue

			elif 'password' in str(value):
				set_clauses.append(f"{key} = (SELECT RIPLRR.LHS_UTILITY.GET_ENCRYPT('{value_to_update}') FROM DUAL)")
			
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

	# frappe.log_error(title="set_clauses", message=set_clauses)

	sql = f"""
		UPDATE {table_name}
		SET
			{', '.join(set_clauses)}
		WHERE
			USER_CODE = '{user_code}'
	"""

	return sql

#----------------Salary Stucture Assignement CRUD Operation

# ERP REFRENCE ---------> SALARY RATE MASTER(RIPLRR.EMP_RATE_MAST)  = SALARY STRUCTURE

# def create_salary_structure_assignment(doc, method):
	
# 	try:
# 		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

# 	except cx_Oracle.DatabaseError as er:
# 		frappe.log_error(title="Oracle Connection Error", message=er)
# 		frappe.throw('Oracle Connection Error:', str(er))

# 	else:
# 		try:
# 			frappe.log_error(title="Salary Structure Assignment", message=doc.as_json())			
# 			cur = con.cursor()

# 			sql_list = get_salary_structure_assignment_insert_query(SALARY_STRUCTURE_RATE_MAST, 'RIPLRR.EMP_RATE_MAST', doc.name)
# 			frappe.log_error(title="Salary Structure Update Query", message=sql_list)
			
# 			# frappe.throw(str(sql_list))
# 			existing_update = 0
# 			emp_code = sql_list[0].get("emp_code")
# 			existing_check_sql = f"SELECT AFNO FROM RIPLRR.EMP_RATE_MAST WHERE EMP_CODE = '{emp_code}' AND TO_DATE IS NULL"
# 			my_count = cur.execute(existing_check_sql)
# 			result = cur.fetchall() 
# 			# frappe.throw(str(result))
# 			if result:
# 				for i in result:
# 					afno = i[0]	
# 					existing_update_sql = f"UPDATE RIPLRR.EMP_RATE_MAST SET TO_DATE = TO_DATE('{doc.from_date} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')  - INTERVAL '1' DAY WHERE EMP_CODE = '{emp_code}' AND AFNO = '{afno}' AND TO_DATE IS NULL"
# 					cur.execute(existing_update_sql)
# 				existing_update = 1

# 			if existing_update == 1:
# 				for sql in sql_list:
# 					cur.execute(sql['query'])


# 			# for sql in sql_list:
# 			# 	existing_check_sql = f"SELECT * FROM RIPLRR.EMP_RATE_MAST WHERE EMP_CODE = '{sql['emp_code']}' AND TO_DATE IS NULL"
# 			# 	my_count = cur.execute(existing_check_sql)
# 			# 	result = cur.fetchall() 
# 			# 	if result:
# 			# 		existing_update_sql = f"UPDATE RIPLRR.EMP_RATE_MAST SET TO_DATE = TO_DATE('{doc.from_date} 00:00:00', 'YYYY-MM-DD HH24:MI:SS') WHERE EMP_CODE = '{sql['emp_code']}' AND TO_DATE IS NULL"
# 			# 		cur.execute(existing_update_sql)
# 			# 		cur.execute(sql['query'])
# 			# 	else:
# 			# 		cur.execute(sql['query'])

# 			con.commit() #-----------------Database commit value
			

# 		except cx_Oracle.DatabaseError as er:
# 			frappe.log_error(title="Oracle Query Error", message=er)
# 			frappe.throw('Oracle Query Error:', str(er))
# 			con.rollback()

# 		except Exception as er:
# 			frappe.log_error(title="Oracle Exception", message=er)
# 			frappe.throw('Oracle Exception:', str(er))
# 			con.rollback()

# 		finally:
# 			if cur:
# 				cur.close()

# 	finally:
# 		if con:
# 			con.close()


# def get_salary_structure_assignment_insert_query(map, table_name, docname):
# 	salary_structure_assignments = frappe.db.sql("""
# 		SELECT
# 			ssa.employee AS emp_code,
# 			ssa.from_date as from_date,
# 			ssa.modified,
# 			CASE 
# 				WHEN sd.parentfield = 'earnings' THEN CONCAT('E', sd.idx)
# 				WHEN sd.parentfield = 'deductions' THEN CONCAT('D', sd.idx)
# 				ELSE sd.idx
# 			END AS afno,
# 			sd.amount as afield,
# 			'rate_identifier' as afrate,
# 			(SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1) AS afcode,
# 			(SELECT custom_erp_code FROM `tabCompany` WHERE name = ssa.company  LIMIT 1) as entity_code,
# 			(SELECT erp_code FROM `tabEmployee Category` WHERE name = e.custom_emp_category LIMIT 1) as custom_emp_category,
# 			(SELECT erp_code FROM `tabPayroll Series` WHERE name = e.custom_payroll_series LIMIT 1) as custom_payroll_series,
# 			(SELECT username FROM `tabUser` WHERE name = ssa.owner) as user_code
# 		FROM
# 			`tabSalary Structure Assignment` as ssa
# 		LEFT JOIN
# 			`tabSalary Detail` as sd ON sd.parent = ssa.salary_structure
# 		LEFT JOIN
# 			`tabEmployee` as e ON e.name = ssa.employee
# 		WHERE
# 			ssa.name = %s
# 	""", (docname), as_dict =1)

# 	if not salary_structure_assignments:
# 		return None

# 	sql_queries = []

# 	for salary_structure_assignment in salary_structure_assignments:
# 		keys = []
# 		values = []
# 		for key, value in map.items():
# 			if value:
# 				keys.append(key)
# 				value_to_insert = salary_structure_assignment[value]
# 				if value_to_insert is None:
# 					values.append('')
# 				elif value_to_insert == 'rate_identifier':
# 					get_indicator_query = f"SELECT COALESCE(AFRATE, 0) AS AFRATE FROM RIPLRR.EMP_CONFIG_MAST WHERE AFCODE = '{salary_structure_assignment['afcode']}' AND EMP_CATG = '{salary_structure_assignment['custom_emp_category']}' AND ENTITY_CODE = '{salary_structure_assignment['entity_code']}' AND TO_DATE IS NULL"
# 					values.append(f'({get_indicator_query})')
# 				else:
# 					if 'from_date' in value:
# 						values.append(f"TO_DATE('{value_to_insert} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')")
# 					elif 'modified' in value:
# 						value_to_insert = str(value_to_insert).split(" ")
# 						values.append(f"TO_DATE('{value_to_insert[0]} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')")
# 					# elif 'afrate' in value:
# 					# 	values.append(value_to_insert)
# 					else:
# 						values.append(f"{value_to_insert}")

# 		formatted_values = []
# 		for elem in values:
# 			if type(elem) == int or type(elem) == float:
# 				formatted_values.append(f"{float(elem)}")
# 			else:
# 				elem_str = str(elem)
# 				if 'TO_DATE' in elem_str:
# 					formatted_values.append(elem_str)
# 				else:
# 					formatted_values.append("'" + elem_str + "'")

# 		sql = f"""
# 			INSERT INTO {table_name}
# 				({','.join([str(elem) for elem in keys])})
# 			VALUES
# 				({','.join(formatted_values)})
# 		"""

# 		query_dict = {"emp_code": f"{salary_structure_assignment['emp_code']}" ,"afno": f"{salary_structure_assignment['afno']}", "date": f"{salary_structure_assignment['modified']}", "query": sql }

# 		sql_queries.append(query_dict)
# 		# frappe.throw(str(query_dict))

# 	return sql_queries



#----------------Salary Slip CRUD Operation

# ERP REFRENCE ---------> SALARY TRANSACTION(RIPLRR.EMP_SAL_TRAN)  = SALARY SLIP

def create_salary_slip(doc, method):
	
	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:
			frappe.log_error(title="Salary slip", message=doc.as_json())			
			cur = con.cursor()



			sql_dict = get_salary_slip_insert_query(SALARY_SLIP_SALARY_TRANS, 'RIPLRR.EMP_SAL_TRAN', doc.name, doc.salary_structure)
			frappe.log_error(title="Salary slip Update Query", message=sql_dict)
			
			sql_list = sql_dict.get("sql_queries")
			emp_code = sql_dict.get("emp_code")
			cal_year = sql_dict.get("cal_year")
			month = sql_dict.get("month")

			# frappe.throw(f"{emp_code} - {cal_year} - {month}")
			check_for_existing_record_sql = f"SELECT * FROM RIPLRR.EMP_SAL_TRAN WHERE EMP_CODE = '{emp_code}' AND CAL_YEAR = '{cal_year}' AND MONTH = '{month}'"
			# frappe.throw(str(check_for_existing_record_sql))

			my_count_for_existing = cur.execute(check_for_existing_record_sql)
			result_for_existing = cur.fetchall() 
			if result_for_existing:
				check_for_transaction_sql = f"SELECT * FROM RIPLRR.EMP_SAL_TRAN WHERE EMP_CODE = '{emp_code}' AND CAL_YEAR = '{cal_year}' AND MONTH = '{month}' AND (ACC_VRNO IS NOT NULL OR ACC_TCODE IS NOT NULL OR PAYMENT_VRNO IS NOT NULL OR PAYMENT_TCODE IS NOT NULL)"
				my_count_for_transaction = cur.execute(check_for_transaction_sql)
				result_for_transaction = cur.fetchall()
				if result_for_transaction:
					frappe.log_error("Salary Transaction Proceed Done", str(result_for_transaction))
					frappe.throw(f"Salary Transaction Already Exist For Employee - {emp_code} AND Month - {month} And Transaction Completed!!")
				else:
					# update query
					sql_update_dict = get_salary_slip_update_query(SALARY_SLIP_SALARY_TRANS, 'RIPLRR.EMP_SAL_TRAN', doc.name, doc.salary_structure)
					frappe.log_error(title="Salary Slip Update Query", message=sql_update_dict)
					sql_update_list = sql_update_dict.get("sql_queries")
					emp_code = sql_update_dict.get("emp_code")
					cal_year = sql_update_dict.get("cal_year")
					month = sql_update_dict.get("month")

					for sql in sql_update_list:
						cur.execute(sql)
			else:
				for sql in sql_list:
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


def get_salary_slip_insert_query(map, table_name, docname, doc_salary_structure):
	salary_slips = frappe.db.sql("""
		SELECT
		employee AS emp_code,
		ss.start_date as from_date,
		EXTRACT(YEAR FROM ss.start_date) AS custom_calendar_year,
		UPPER(TRIM(TO_CHAR(ss.start_date, 'MON'))) AS custom_month,
		ss.modified,
		sd.parentfield,
		CASE 
			WHEN sd.parentfield = 'earnings' THEN CONCAT('E', sd.idx)
			WHEN sd.parentfield = 'deductions' THEN CONCAT('D', sd.idx)
			ELSE sd.idx
		END AS afno,
		(SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1) AS afcode,
		LEFT(UPPER(sd.salary_component), 15) AS afhead,
		sd.custom_erp_rate AS afrate,
		'rate_identifier' AS afratei,
		(SELECT custom_erp_code FROM `tabCompany` WHERE name = ss.company  LIMIT 1) as entity_code,
		(SELECT erp_code FROM `tabDivision` WHERE name = ss.custom_division  LIMIT 1) as custom_division,
		(SELECT erp_code FROM `tabEmployee Category` WHERE name = ss.custom_employee_category LIMIT 1) as custom_emp_category,
		(SELECT erp_code FROM `tabPayroll Series` WHERE name = ss.custom_payroll_series LIMIT 1) as custom_payroll_series,
		(SELECT username FROM `tabUser` WHERE name = ss.owner) as user_code,
		IFNULL((SELECT ss_sd.amount FROM `tabSalary Detail` as ss_sd WHERE ss_sd.parent = ss.name AND (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = ss_sd.salary_component LIMIT 1) = (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1)), 0) AS afield,
		IFNULL((SELECT ss_sd.amount FROM `tabSalary Detail` as ss_sd WHERE ss_sd.parent = ss.name AND (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = ss_sd.salary_component LIMIT 1) = (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1)), 0) AS actuals
	FROM
		`tabSalary Slip` as ss
	LEFT JOIN
		`tabSalary Detail` as sd ON sd.parent = ss.salary_structure
	WHERE
		ss.name = %s
	""", (docname), as_dict =1)

	if not salary_slips:
		return None

	sql_queries = []
	for salary_slip in salary_slips:
		keys = []
		values = []
		for key, value in map.items():
			if value:
				keys.append(key)
				value_to_insert = salary_slip[value]
				if value_to_insert is None:
					values.append('')
				elif value_to_insert == 'rate_identifier':
					get_indicator_query = f"SELECT AFRATEI FROM RIPLRR.EMP_CONFIG_MAST WHERE AFCODE = '{salary_slip['afcode']}' AND EMP_CATG = '{salary_slip['custom_emp_category']}' AND ENTITY_CODE = '{salary_slip['entity_code']}' AND TO_DATE IS NULL"
					values.append(f'({get_indicator_query})')
				else:
					if 'from_date' in value:
						values.append(f"TO_DATE('{value_to_insert} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')")
					elif 'modified' in value:
						value_to_insert = str(value_to_insert).split(".")
						values.append(f"TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
					elif 'afrate' in value:
						values.append(value_to_insert)
					else:
						values.append(f"{value_to_insert}")

		formatted_values = []
		for elem in values:
			if type(elem) == int or type(elem) == float:
				formatted_values.append(f"{float(elem)}")
			else:
				elem_str = str(elem)
				if 'TO_DATE' in elem_str:
					formatted_values.append(elem_str)
				else:
					formatted_values.append("'" + elem_str + "'")
		sql = f"""
			INSERT INTO {table_name}
				({','.join([str(elem) for elem in keys])})
			VALUES
				({','.join(formatted_values)})
		"""

		sql_queries.append(sql)
	
	sql_dict = {"sql_queries":sql_queries, "emp_code": salary_slips[0].emp_code, "cal_year": salary_slips[0].custom_calendar_year, "month":  salary_slips[0].custom_month }
	
	return sql_dict


def get_salary_slip_update_query(map, table_name, docname, doc_salary_structure):
	salary_slips = frappe.db.sql("""
		SELECT
		employee AS emp_code,
		ss.start_date as from_date,
		EXTRACT(YEAR FROM ss.start_date) AS custom_calendar_year,
		UPPER(TRIM(TO_CHAR(ss.start_date, 'MON'))) AS custom_month,
		ss.modified,
		sd.parentfield,
		CASE 
			WHEN sd.parentfield = 'earnings' THEN CONCAT('E', sd.idx)
			WHEN sd.parentfield = 'deductions' THEN CONCAT('D', sd.idx)
			ELSE sd.idx
		END AS afno,
		(SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1) AS afcode,
		LEFT(UPPER(sd.salary_component), 15) AS afhead,
		sd.custom_erp_rate AS afrate,
		'rate_identifier' AS afratei,
		(SELECT custom_erp_code FROM `tabCompany` WHERE name = ss.company  LIMIT 1) as entity_code,
		(SELECT erp_code FROM `tabDivision` WHERE name = ss.custom_division  LIMIT 1) as custom_division,
		(SELECT erp_code FROM `tabEmployee Category` WHERE name = ss.custom_employee_category LIMIT 1) as custom_emp_category,
		(SELECT erp_code FROM `tabPayroll Series` WHERE name = ss.custom_payroll_series LIMIT 1) as custom_payroll_series,
		(SELECT username FROM `tabUser` WHERE name = ss.owner) as user_code,
		IFNULL((SELECT ss_sd.amount FROM `tabSalary Detail` as ss_sd WHERE ss_sd.parent = ss.name AND (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = ss_sd.salary_component LIMIT 1) = (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1)), 0) AS afield,
		IFNULL((SELECT ss_sd.amount FROM `tabSalary Detail` as ss_sd WHERE ss_sd.parent = ss.name AND (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = ss_sd.salary_component LIMIT 1) = (SELECT custom_erp_code FROM `tabSalary Component` WHERE name = sd.salary_component LIMIT 1)), 0) AS actuals
	FROM
		`tabSalary Slip` as ss
	LEFT JOIN
		`tabSalary Detail` as sd ON sd.parent = ss.salary_structure
	WHERE
		ss.name = %s
	""", (docname), as_dict =1)

	

	if not salary_slips:
		return None

	sql_queries = []
	for salary_slip in salary_slips:
		sets = []
		conditions = []
		for key, value in map.items():
			if value:
				if value == 'emp_code':
					conditions.append(f"{key} = '{salary_slip[value]}' AND AFNO = '{salary_slip['afno']}' AND CAL_YEAR = '{salary_slip['custom_calendar_year']}' AND MONTH = '{salary_slip['custom_month']}' ")
				else:
					value_to_insert = salary_slip[value]
					if value_to_insert is None:
						sets.append(f"{key} = ''")
					elif value_to_insert == 'rate_identifier':
						get_indicator_query = f"SELECT AFRATEI FROM RIPLRR.EMP_CONFIG_MAST WHERE AFCODE = '{salary_slip['afcode']}' AND EMP_CATG = '{salary_slip['custom_emp_category']}' AND ENTITY_CODE = '{salary_slip['entity_code']}' AND TO_DATE IS NULL"
						sets.append(f"{key} = ({get_indicator_query})")
					else:
						if 'from_date' in value:
							sets.append(f"{key} = TO_DATE('{value_to_insert} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')")
						elif 'modified' in value:
							value_to_insert = str(value_to_insert).split(".")
							sets.append(f"{key} = TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
						elif 'afrate' in value:
							sets.append(f"{key} = {value_to_insert}")
						else:
							sets.append(f"{key} = '{value_to_insert}'")

		sql = f"""
			UPDATE {table_name}
			SET {','.join([str(elem) for elem in sets])}
			WHERE {' AND '.join([str(elem) for elem in conditions])}
		"""

		sql_queries.append(sql)
	
	sql_dict = {"sql_queries":sql_queries, "emp_code": salary_slips[0].emp_code, "cal_year": salary_slips[0].custom_calendar_year, "month":  salary_slips[0].custom_month }
	
	return sql_dict


def get_attendance_balance_insert_query(map, table_name, docname, doc_salary_structure):
	salary_slip = frappe.db.sql("""
		SELECT
			EXTRACT(YEAR FROM ss.end_date) AS custom_calendar_year,
			EXTRACT(MONTH FROM ss.end_date) AS custom_month,
			employee AS emp_code,
			(SELECT custom_erp_code FROM `tabCompany` WHERE name = ss.company  LIMIT 1) as entity_code,
			ss.company,
			ss.modified,
			(SELECT username FROM `tabUser` WHERE name = ss.owner) as user_code
		FROM
			`tabSalary Slip` as ss
		WHERE
			ss.name = %s
		""", (docname), as_dict =1)

	cal_year = salary_slip[0].get("custom_calendar_year")
	month = salary_slip[0].get("month")
	employee = salary_slip[0].get("emp_code")
	company = salary_slip[0].get("company")
	lastupdate = salary_slip[0].get("modified")
	usercode = salary_slip[0].get("user_code")

	result = frappe.call(
		"frappe.desk.query_report.run",
		report_name="Monthly Attendance Sheet",
		filters={
			"month":month,
			"year":cal_year,
			"employee":employee,
			"company":company,
			"summarized_view":1
		},
		ignore_prepared_report=True
		)

	temp_result = result["result"][0]

	leave_type = frappe.db.get_all("Leave Type", ["name", "custom_attend_char"])

	leaves =  ["NIGHT", "TOUR", "APPROVED_LEAVE", "PRESENT", "COMPENSATORY_OFF", "ABSENT_LOP", "WEEKLY_OFF", "CASUAL_LEAVE", "HOLIDAY", "EARNED_LEAVE", "ESIC_LEAVE", "OUTDOOR_DUTY_LEAVE", "SICK_LEAVE", "OPTIONAL_LEAVE", "LATE_PENALTY", "FULL_AND_FINAL_EARNING", "FULL_AND_FINAL_DEDUCTION"]

	main_rec = []

	for leave in  leaves:
		for rec in main_rec:
			if rec.name != leave.lower():
				leavetype = ""
				for l_typ in leave_type:
					if l_typ.get("name") == rec.name:
						leavetype = name 
				temp_rec = {
					"cal_year" : cal_year,
					"month" : month,
					"employee" : employee,
					"company" : company,
					"lastupdate" : lastupdate,
					"usercode" : usercode,
					"name" : leavetype
				}
				if temp_rec.leavetype != "":
					main_rec.append(temp_rec)

		pass

	if not salary_slips:
		return None

	sql_queries = []
	for salary_slip in salary_slips:
		sets = []
		conditions = []
		for key, value in map.items():
			if value:
				if value == 'emp_code':
					conditions.append(f"{key} = '{salary_slip[value]}' AND AFNO = '{salary_slip['afno']}' AND CAL_YEAR = '{salary_slip['custom_calendar_year']}' AND MONTH = '{salary_slip['custom_month']}' ")
				else:
					value_to_insert = salary_slip[value]
					if value_to_insert is None:
						sets.append(f"{key} = ''")
					elif value_to_insert == 'rate_identifier':
						get_indicator_query = f"SELECT AFRATEI FROM RIPLRR.EMP_CONFIG_MAST WHERE AFCODE = '{salary_slip['afcode']}' AND EMP_CATG = '{salary_slip['custom_emp_category']}' AND ENTITY_CODE = '{salary_slip['entity_code']}' AND TO_DATE IS NULL"
						sets.append(f"{key} = ({get_indicator_query})")
					else:
						if 'from_date' in value:
							sets.append(f"{key} = TO_DATE('{value_to_insert} 00:00:00', 'YYYY-MM-DD HH24:MI:SS')")
						elif 'modified' in value:
							value_to_insert = str(value_to_insert).split(".")
							sets.append(f"{key} = TO_DATE('{value_to_insert[0]}', 'YYYY-MM-DD HH24:MI:SS')")
						elif 'afrate' in value:
							sets.append(f"{key} = {value_to_insert}")
						else:
							sets.append(f"{key} = '{value_to_insert}'")

		sql = f"""
			UPDATE {table_name}
			SET {','.join([str(elem) for elem in sets])}
			WHERE {' AND '.join([str(elem) for elem in conditions])}
		"""

		sql_queries.append(sql)
	
	sql_dict = {"sql_queries":sql_queries, "emp_code": salary_slips[0].emp_code, "cal_year": salary_slips[0].custom_calendar_year, "month":  salary_slips[0].custom_month }
	
	return sql_dict






# Fetch ERP Config Master Details From this
@frappe.whitelist()
def config_master():
	# emp_code = frappe.form_dict.emp_code
	emp_catg = frappe.form_dict.emp_catg
	company = frappe.form_dict.company

	category = frappe.db.get_value("Employee Category", emp_catg, "erp_code")
	company = frappe.db.get_value("Company", company, "custom_erp_code")

	# value = frappe.db.sql("""
	# 	SELECT 
	# 		(SELECT custom_erp_code FROM `tabCompany` WHERE name = e.company  LIMIT 1) as entity_code,
	# 		(SELECT erp_code FROM `tabEmployee Category` WHERE name = e.custom_emp_category LIMIT 1) as custom_emp_category
	# 	FROM
	# 		`tabEmployee` as e
	# 	WHERE
	# 		e.name = %s
	# 	""", (emp_code), as_dict=1)
	
	# msg = f'{emp_code} - {emp_catg} - {company} , {str(value[0].entity_code)} , {str(value[0].custom_emp_category)}'

	try:
		con = cx_Oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

	except cx_Oracle.DatabaseError as er:
		frappe.log_error(title="Oracle Connection Error", message=er)
		frappe.throw('Oracle Connection Error:', str(er))

	else:
		try:		
			cur = con.cursor()
			if category == None or company == None:
				frappe.throw(f"ERP Code Not Found For Category or Company")
				
			else:
				sql_query = f"""
					SELECT 
						AFNO,
						AFCODE,
						AFHEAD,
						AFRATEI,
						AFRATE
					FROM 
						RIPLRR.EMP_CONFIG_MAST 
					WHERE 
						EMP_CATG = '{category}' 
						AND ENTITY_CODE = '{company}' 
						AND TO_DATE IS NULL
					ORDER BY
						SUBSTR(AFNO, 1, 1),
						TO_NUMBER(SUBSTR(AFNO, 2))
					"""
				
				components = cur.execute(sql_query)
				result = cur.fetchall()

				result_list = []
				for row in result:
					result_dict = {}
					for idx, col in enumerate(cur.description):
						if isinstance(row[idx], datetime):
							result_dict[col[0]] = row[idx].isoformat()
						else:
							result_dict[col[0]] = row[idx]
					result_list.append(result_dict)

				for rec in result_list:
					if rec.get("AFCODE"):
						salary_component = frappe.db.get_value("Salary Component", {"custom_erp_code": rec.get("AFCODE")}, "name")
						salary_component_abbr = frappe.db.get_value("Salary Component", {"custom_erp_code": rec.get("AFCODE")}, "salary_component_abbr")
						rec["salary_component"] = salary_component
						rec["abbr"] = salary_component_abbr


				json_result = json.dumps(result_list)
				frappe.log_error("MSG_result", json_result)



				msg = json_result

			# con.commit() #-----------------Database commit value
			
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

	return msg


