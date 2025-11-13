# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class GatePass(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amended_from: DF.Link | None
        date: DF.Date
        employee: DF.Link
        employee_name: DF.Data | None
        name: DF.Int | None
        reason: DF.SmallText
    # end: auto-generated types
    pass
