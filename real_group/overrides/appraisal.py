from frappe.utils import flt
from hrms.hr.doctype.appraisal.appraisal import Appraisal


class AppraisalOverride(Appraisal):
    def calculate_final_score(self):
        goal_score = flt(self.total_score)
        feedback_score = flt(self.avg_feedback_score)
        self_score = flt(self.self_score)

        if feedback_score <= 0:
            final_score = 0
        elif goal_score > 0 and self_score > 0:
            final_score = (goal_score + feedback_score + self_score) / 3
        elif goal_score > 0:
            final_score = (goal_score + feedback_score) / 2
        elif self_score > 0:
            final_score = (feedback_score + self_score) / 2
        else:
            final_score = feedback_score

        self.final_score = int(final_score + 0.5)
