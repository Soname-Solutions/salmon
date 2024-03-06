from .general_aws_event_mapper import GeneralAwsEventMapper
from .general_aws_event_mapper import ExecutionInfoUrlMixin
from ...settings import Settings
from ...core.constants import EventResult
from ...aws.glue_manager import GlueManager


class GlueCrawlerEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["crawlerName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        if self.get_resource_state() in GlueManager.Crawlers_States_Failure:
            return EventResult.FAILURE
        elif self.get_resource_state() in GlueManager.Crawlers_States_Success:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def get_execution_info_url(self, resource_name: str):
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
        )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(
                ["Crawler Name", self.event["detail"]["crawlerName"]]
            )
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )
        rows.append(
            super().create_table_row(["Message", self.event["detail"]["message"]])
        )

        return message_body
