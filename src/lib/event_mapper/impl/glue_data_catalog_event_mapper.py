from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from ...core.constants import EventResult


class GlueDataCatalogEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self, event):
        return event["detail"]["databaseName"]

    def get_resource_state(self, event):
        return event["detail"]["state"]

    def get_event_result(self, event):
        return EventResult.INFO

    def get_message_body(self, event):
        message_body, rows = super().create_message_body_with_common_rows(event)

        style = super().get_row_style(event)

        rows.append(
            super().create_table_row(["Database Name", event["detail"]["databaseName"]])
        )
        rows.append(
            super().create_table_row(
                ["Type of Change", event["detail"]["typeOfChange"]]
            )
        )

        return message_body
