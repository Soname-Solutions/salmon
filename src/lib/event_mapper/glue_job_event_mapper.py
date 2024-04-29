from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.aws.glue_manager import GlueManager


class GlueJobEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["jobName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        if self.get_resource_state() in GlueManager.Job_States_Failure:
            return EventResult.FAILURE
        elif self.get_resource_state() in GlueManager.Job_States_Success:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def get_execution_info_url(self, resource_name: str):
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
            run_id=self.event["detail"]["jobRunId"],
        )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["Job Name", self.event["detail"]["jobName"]])
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )

        link_url = self.get_execution_info_url(self.get_resource_name())
        run_id = self.event["detail"]["jobRunId"]
        rows.append(
            super().create_table_row(
                ["Glue Job Run ID", f"<a href='{link_url}'>{run_id}</a>"]
            )
        )
        rows.append(
            super().create_table_row(["Message", self.event["detail"]["message"]])
        )

        return message_body
