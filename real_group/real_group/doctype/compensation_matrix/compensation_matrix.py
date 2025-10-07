# Copyright (c) 2024, Step Tech and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompensationMatrix(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from real_group.real_group.doctype.compensation_matrix_details.compensation_matrix_details import (
            CompensationMatrixDetails,
        )

        description: DF.Data
        items: DF.Table[CompensationMatrixDetails]
        shift_duration: DF.Time
    # end: auto-generated types
    pass
