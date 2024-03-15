from .general_aws_event_mapper import GeneralAwsEventMapper
from .general_aws_event_mapper import ExecutionInfoUrlMixin
from ...settings import Settings
from ...core.constants import EventResult
from ...aws.glue_manager import GlueManager


class GlueDataCatalogEventMapperException(Exception):
    """Exception raised for errors encountered while running Glue client methods."""

    pass


class GlueDataCatalogEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["databaseName"]

    def get_resource_state(self):
        state = self.event["detail"].get("state", None)

        if state is None:
            if self.event["detail-type"].startswith("Glue Data Catalog"):
                state = GlueManager.Catalog_State_Success
            else:
                raise GlueDataCatalogEventMapperException(
                    f"Required state is not defined in event: {self.event}"
                )

        return state

    def get_event_result(self):
        return (
            EventResult.SUCCESS
            if self.get_resource_state() == GlueManager.Catalog_State_Success
            else EventResult.FAILURE
        )

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
                ["Database Name", self.event["detail"]["databaseName"]]
            )
        )
        rows.append(
            super().create_table_row(
                ["Type of Change", self.event["detail"]["typeOfChange"]]
            )
        )

        return message_body
