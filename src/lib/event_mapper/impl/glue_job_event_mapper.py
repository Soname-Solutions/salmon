from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from ...core.constants import EventResult
from ...aws.glue_manager import GlueManager


class GlueJobEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["jobName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        if self.get_resource_state(self.event) in GlueManager.Job_States_Failure:
            return EventResult.FAILURE
        elif self.get_resource_state(self.event) in GlueManager.Job_States_Success:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(super().create_table_row(["Job Name", self.event["detail"]["jobName"]]))
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )
        rows.append(super().create_table_row(["JobRunID", self.event["detail"]["jobRunId"]]))
        rows.append(super().create_table_row(["Message", self.event["detail"]["message"]]))

        return message_body
