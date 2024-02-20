from .general_aws_event_mapper import GeneralAwsEventMapper
from .general_aws_event_mapper import ExecutionInfoUrlMixin
from ...settings import Settings
from ...core.constants import EventResult


class GlueDataCatalogEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["databaseName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        return EventResult.INFO

    def get_execution_info_url(self, resource_type: str, resource_name: str):
        return ExecutionInfoUrlMixin.get_execution_info_url(
            resource_type=resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
        )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(
                ["Database Name", self.event["detail"]["databaseName"]]
            )
        )
        rows.append(
            super().create_table_row(
                ["Type of Change", self.event["detail"]["typeOfChange"]]
            )
        )

        return message_body
