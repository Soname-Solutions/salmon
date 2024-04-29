from lib.event_mapper.general_aws_event_mapper import GeneralAwsEventMapper
from lib.core.constants import EventResult
from lib.aws.glue_manager import GlueManager


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
        # Sample Details:
        # "detail": {
        #     "databaseName": "testdb1",  # this field is always present
        #     "changedPartitions": [],
        #     "typeOfChange": "UpdateTable", or "CreateTable" or "CreateDatabase"
        #     "tableName": "tbl1", <- cases a) Db-level -> field is not present, b) this field is present
        #     "changedTables": ["tbl1"], <- sometimes this field is present instead of "tableName"
        # },
        try:
            type_of_change = self.event["detail"].get("typeOfChange", "")
            region_name = self.event["region"]
            database_name = self.event["detail"]["databaseName"]

            if "Table" in type_of_change:
                table_name = self.event["detail"].get("tableName")
                if table_name is None:
                    table_name = self.event["detail"].get("changedTables")[0]

                return (
                    f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/data-catalog/tables/view/{table_name}?database={database_name}",
                )
            else:
                return f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/data-catalog/databases/view/{database_name}"
        except Exception as e:
            raise GlueDataCatalogEventMapperException(
                f"Error getting execution info URL: {e}"
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
        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                [
                    "Execution Info",
                    f"<a href='{link_url}'>Link to AWS Console</a>",
                ]
            )
        )

        return message_body
