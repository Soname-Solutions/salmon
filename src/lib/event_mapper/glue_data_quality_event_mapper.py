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
        context = self.event.get("detail", {}).get("context", {})
        context_type = context.get("contextType")

        if context_type == "GLUE_DATA_CATALOG":
            return ExecutionInfoUrlMixin.get_url(
                resource_type=self.resource_type,
                region_name=self.event["region"],
                resource_name=resource_name,
                run_id=context.get("runId"),
                context_type=context_type,
                glue_table_name=context.get("tableName"),
                glue_db_name=context.get("databaseName"),
                glue_catalog_id=context.get("catalogId"),
            )
        elif context_type == "GLUE_JOB":
            return ExecutionInfoUrlMixin.get_url(
                resource_type=self.resource_type,
                region_name=self.event["region"],
                resource_name=resource_name,
                run_id=context.get("jobId"),
                glue_job_name=context.get("jobName"),
                context_type=context_type,
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

        context = self.event.get("detail", {}).get("context", {})
        if context.get("contextType") == "GLUE_DATA_CATALOG":
            rows.append(
                super().create_table_row(["Glue Table Name", context.get("tableName")])
            )
            rows.append(
                super().create_table_row(
                    [
                        "Glue Database Name",
                        context.get("databaseName"),
                    ]
                )
            )
            run_id = context.get("runId")
        else:
            rows.append(
                super().create_table_row(["Glue Job Name", context.get("jobName")])
            )
            run_id = context.get("jobId")

        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                ["Glue DQ Run ID", f"<a href='{link_url}'>{run_id}</a>"]
            )
        )

        return message_body
