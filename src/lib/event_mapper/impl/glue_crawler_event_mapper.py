from .general_aws_event_mapper import GeneralAwsEventMapper
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

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["Crawler Name", self.event["detail"]["crawlerName"]])
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )
        rows.append(super().create_table_row(["Message", self.event["detail"]["message"]]))

        return message_body
