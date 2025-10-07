import cx_Oracle
import frappe
from frappe.core.doctype.user.user import _get_user_for_update_password
from frappe.core.doctype.user.user import update_password as _update_password

from real_group.real_group.integration import oracle_connection


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_user_password(
    new_password: str, logout_all_sessions: int = 0, key: str | None = None, old_password: str | None = None
):
    res = _get_user_for_update_password(key, old_password)
    if res.get("message"):
        frappe.local.response.http_status_code = 410
        return res["message"]

    user = res["user"]

    if user == "Administrator":
        return _update_password(new_password, logout_all_sessions, key, old_password)

    if not frappe.db.exists("Employee", user):
        frappe.throw(f"Employee not found for the user -> {user}")
    company = frappe.db.get_value("Employee", user, "company")

    con = oracle_connection(company)
    if not con:
        frappe.throw(title="Oracle Connection information is not set")

    try:
        with con.cursor() as cur:
            cur.execute("SELECT USER_CODE FROM RIPLRR.USER_MAST WHERE USER_CODE = :user", user=user)
            if not cur.fetchall():
                frappe.throw(frappe._("User not found in Oracle DB!! Kindly Create User"))

            cur.execute(
                """
                UPDATE RIPLRR.USER_MAST
                SET PASSWORD = (SELECT RIPLRR.LHS_UTILITY.GET_ENCRYPT(:new_password) FROM DUAL),
                    LASTUPDATE = TIMESTAMP :now
                WHERE USER_CODE = :user
                """,
                new_password=new_password,
                now=frappe.utils.now(),
                user=user,
            )

        try:
            response = _update_password(new_password, logout_all_sessions, key, old_password)
        except Exception as e:
            frappe.log_error(title="Frappe Password Update Error", message=str(e))
            raise

        con.commit()
        return response

    except cx_Oracle.DatabaseError as er:
        con.rollback()
        frappe.log_error(title="Oracle Query Error", message=str(er))
        frappe.throw(f"Oracle Query Error: {er!s}")

    except Exception as er:
        con.rollback()
        frappe.log_error(title="Unexpected Exception", message=str(er))
        raise

    finally:
        con.close()
