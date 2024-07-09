from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.aws.glue_manager import GlueManager
from lib.core.constants import SettingConfigResourceTypes as types


class GlueDataQualityEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["rulesetNames"][0]

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
        if self.event["detail"]["context"]["contextType"] == "GLUE_DATA_CATALOG":
            return ExecutionInfoUrlMixin.get_url(
                resource_type=self.resource_type,
                region_name=self.event["region"],
                resource_name=resource_name,
                run_id=self.event["detail"]["context"]["runId"],
                glue_table_name=self.event["detail"]["context"]["tableName"],
                glue_db_name=self.event["detail"]["context"]["databaseName"],
                glue_catalog_id=self.event["detail"]["context"]["catalogId"],
            )
        elif self.event["detail"]["context"]["contextType"] == "GLUE_JOB":
            return ExecutionInfoUrlMixin.get_url(
                resource_type=types.GLUE_JOBS,
                region_name=self.event["region"],
                resource_name=self.event["detail"]["context"]["jobName"],
                run_id=self.event["detail"]["context"]["jobId"],
            )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["Glue DQ Ruleset Name", self.get_resource_name()])
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )

        if self.event["detail"]["context"]["contextType"] == "GLUE_DATA_CATALOG":
            rows.append(
                super().create_table_row(
                    ["Glue Table Name", self.event["detail"]["context"]["tableName"]]
                )
            )
            rows.append(
                super().create_table_row(
                    [
                        "Glue Database Name",
                        self.event["detail"]["context"]["databaseName"],
                    ]
                )
            )
            run_id = self.event["detail"]["context"]["runId"]
        else:
            rows.append(
                super().create_table_row(
                    ["Glue Job Name", self.event["detail"]["context"]["jobName"]]
                )
            )
            run_id = self.event["detail"]["context"]["jobId"]

        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                ["Glue DQ Run ID", f"<a href='{link_url}'>{run_id}</a>"]
            )
        )

        return message_body
