from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.aws.glue_manager import GlueManager


class GlueDataQualityEventMapperException(Exception):
    pass


class GlueDataQualityEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        try:
            ruleset_name = self.event["detail"]["rulesetNames"][0]
            return ruleset_name
        except (KeyError, IndexError):
            raise GlueDataQualityEventMapperException(
                f"Required GLue DQ Ruleset name is not defined in the DQ event: {self.event}"
            )

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        if self.get_resource_state() in GlueManager.Data_Quality_Failure:
            return EventResult.FAILURE
        elif self.get_resource_state() in GlueManager.Data_Quality_Success:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def _get_context_and_run_id(self):
        context = self.event.get("detail", {}).get("context", {})
        context_type = context.get("contextType")

        if context_type not in GlueManager.Data_Quality_Context_Types:
            raise GlueDataQualityEventMapperException(
                f"Unknown or missing context type in the DQ event: {self.event}"
            )

        run_id_key_map = {"GLUE_DATA_CATALOG": "runId", "GLUE_JOB": "jobId"}
        run_id = context.get(run_id_key_map[context_type])
        if not run_id:
            raise GlueDataQualityEventMapperException(
                f"Missing run ID for context type {context_type} in the DQ event: {self.event}"
            )

        return context, context_type, run_id

    def get_execution_info_url(self, resource_name: str):
        context, context_type, run_id = self._get_context_and_run_id()

        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
            run_id=run_id,
            context_type=context_type,
            glue_table_name=context.get("tableName"),
            glue_db_name=context.get("databaseName"),
            glue_catalog_id=context.get("catalogId"),
            glue_job_name=context.get("jobName"),
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

        context, context_type, run_id = self._get_context_and_run_id()
        if context_type == "GLUE_DATA_CATALOG":
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
        elif context_type == "GLUE_JOB":
            rows.append(
                super().create_table_row(["Glue Job Name", context.get("jobName")])
            )

        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                ["Glue DQ Run ID", f"<a href='{link_url}'>{run_id}</a>"]
            )
        )

        return message_body
