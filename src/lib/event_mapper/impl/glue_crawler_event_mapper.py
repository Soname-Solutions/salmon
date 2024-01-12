from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from ...core.constants import EventResult


class GlueCrawlerEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        return event["detail"]["crawlerName"]

    def get_resource_state(self, event):
        return event["detail"]["state"]

    def get_event_result(self, event):
        if self.get_resource_state(event) == "Failed":
            return EventResult.ERROR
        if self.get_resource_state(event) == "Succeeded":
            return EventResult.SUCCESS
        return EventResult.INFO

    def get_message_body(self, event):
        message_body, rows = super().create_message_body_with_common_rows(event)

        style = super().get_row_style(event)

        rows.append(
            super().create_table_row(["Crawler Name", event["detail"]["crawlerName"]])
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state(event)], style)
        )
        rows.append(super().create_table_row(["Message", event["detail"]["message"]]))

        return message_body
