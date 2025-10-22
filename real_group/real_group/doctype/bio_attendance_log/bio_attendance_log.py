# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

from datetime import datetime, time

from frappe.model.document import Document
from frappe.utils import get_timedelta, getdate


class BioAttendanceLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        area: DF.Data | None
        employee: DF.Link
        is_processed: DF.Literal["", "N", "Y", "E"]
        message: DF.Text | None
        name: DF.Int | None
        punch_date: DF.Date | None
        punch_datetime: DF.Datetime | None
        punch_datetime_backup: DF.Datetime | None
        punch_direction: DF.Literal["", "I", "O"]
        punch_time: DF.Time | None
        terminal_id: DF.Data | None
        time_pro_reference_id: DF.Data | None
    # end: auto-generated types
    pass

    def validate(self):
        if self.punch_date and self.punch_time:
            punch_time = get_timedelta(self.punch_time)
            punch_date = getdate(self.punch_date)
            self.punch_datetime = datetime.combine(punch_date, time.min) + punch_time
