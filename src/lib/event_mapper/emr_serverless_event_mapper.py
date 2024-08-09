from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.aws.emr_manager import EMRManager
from lib.settings import Settings


class EMRServerlessEventMapper(GeneralAwsEventMapper):
    def __init__(self, resource_type: str, event: dict, settings: Settings):
        super().__init__(resource_type, event, settings)

        self.event_details = self.event["detail"]
        self.app_id = self.event_details.get("applicationId")
        self.run_id = self.event_details.get("jobRunId")
        self.emr_manager = EMRManager()

    def get_resource_name(self):
        """Retrieve the EMR Serverless application name."""
        if not self.app_id:
            raise ValueError(
                f"EMR Serverless Application ID is not defined in the event: {self.event}"
            )
        return self.emr_manager.get_application_name(app_id=self.app_id)

    def get_resource_state(self):
        return self.event_details["state"]

    def get_event_result(self):
        if self.get_resource_state() in EMRManager.STATES_FAILURE:
            return EventResult.FAILURE
        elif self.get_resource_state() in EMRManager.STATES_SUCCESS:
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

        if not self.run_id:
            raise ValueError(
                f"EMR Job Run ID is not defined in the event: {self.event}"
            )

        # extract job details (job name, error message, script location)
        job_run = self.emr_manager.get_job_run(app_id=self.app_id, run_id=self.run_id)
        job_run_name = job_run.name
        message = job_run.ErrorMessage
        script_location = (
            job_run.jobDriver.sparkSubmit.entryPoint
            if job_run.jobDriver and job_run.jobDriver.sparkSubmit
            else None
        )

        rows.append(
            super().create_table_row(
                ["EMR Serverless Application Name", self.get_resource_name()]
            )
        )

        if job_run_name:
            rows.append(
                super().create_table_row(["EMR Serverless Job Name", job_run_name])
            )

        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )
        rows.append(super().create_table_row(["Job Run ID", self.run_id]))

        # add script location for the Spark submit job run if it exists
        if script_location:
            rows.append(super().create_table_row(["Script Location", script_location]))

        # add a link to the Amazon EMR Console
        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                ["Console URL", f"<a href='{link_url}'>Link to Amazon EMR Console</a>"]
            )
        )

        # add the error message if it exists
        if message:
            rows.append(super().create_table_row(["Message", message]))

        return message_body
