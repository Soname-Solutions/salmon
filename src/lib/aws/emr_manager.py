import boto3
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

from lib.core.constants import MessageSettings as msg


################################################################
class SparkSubmit(BaseModel):
    # script location
    entryPoint: str


class JobDriver(BaseModel):
    sparkSubmit: Optional[SparkSubmit]


class ResourceUtilization(BaseModel):
    vCPUHour: Optional[float] = None
    memoryGBHour: Optional[float] = None
    storageGBHour: Optional[float] = None


class EMRJobRunData(BaseModel):
    applicationId: str
    jobRunId: str
    name: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    state: str
    stateDetails: Optional[str] = None
    jobDriver: Optional[JobDriver] = None
    totalResourceUtilization: Optional[ResourceUtilization] = Field(
        default_factory=ResourceUtilization
    )
    totalExecutionDurationSeconds: Optional[int] = None
    billedResourceUtilization: Optional[ResourceUtilization] = Field(
        default_factory=ResourceUtilization
    )

    @property
    def IsSuccess(self) -> bool:
        return self.state in EMRManager.STATES_SUCCESS

    @property
    def IsFailure(self) -> bool:
        return self.state in EMRManager.STATES_FAILURE

    @property
    def ErrorMessage(self) -> Optional[str]:
        if not self.stateDetails:
            return None

        # remove the general sentence from the error details
        error_message = self.stateDetails.replace(
            "Job failed, please check complete logs in configured logging destination.",
            "",
        ).strip()

        # trim the error message if it exceeds MAX_ERROR_MESSAGE_LENGTH
        if len(error_message) > msg.MAX_ERROR_MESSAGE_LENGTH:
            error_message = error_message[: msg.MAX_ERROR_MESSAGE_LENGTH] + "..."
        return error_message


class EMRJobRunResponse(BaseModel):
    jobRun: EMRJobRunData


################################################################


class EMRManagerException(Exception):
    """Exception raised for errors encountered while running EMR client methods."""

    pass


class EMRManager:
    STATES_SUCCESS = ["SUCCESS"]
    STATES_FAILURE = ["FAILED", "CANCELLED"]
    # FYI: all states = 'SUBMITTED'|'PENDING'|'SCHEDULED'|'RUNNING'|'SUCCESS'|'FAILED'|'CANCELLING'|'CANCELLED'

    def __init__(self, sf_client=None):
        self.sf_client = (
            boto3.client("emr-serverless") if sf_client is None else sf_client
        )

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        return state in cls.STATES_SUCCESS or state in cls.STATES_FAILURE

    def get_all_names(self, **kwargs):
        """Get all EMR Serverless application names"""

        try:
            response = self.sf_client.list_applications()
            return [res["name"] for res in response.get("applications")]

        except Exception as e:
            error_message = f"Error getting a list of EMR applications: {e}"
            raise EMRManagerException(error_message)

    def get_application_name(self, app_id: str) -> str:
        """Get EMR Serverless application name by its ID"""

        try:
            response = self.sf_client.get_application(applicationId=app_id)
            return response.get("application").get("name")

        except Exception as e:
            error_message = f"Error getting a name of EMR application ID {app_id}: {e}"
            raise EMRManagerException(error_message)

    def get_application_id_by_name(self, app_name: str) -> str:
        """Get EMR Serverless application ID by its name"""

        try:
            response = self.sf_client.list_applications()
            applications = response.get("applications", [])

            for app in applications:
                if app.get("name") == app_name:
                    return app.get("id")
            return None

        except Exception as e:
            error_message = f"Error getting EMR app ID by its name: {e}"
            raise EMRManagerException(error_message)

    def get_job_run(self, app_id: str, run_id: str) -> str:
        """Get detailed information about a job run submitted to the EMR Serverless application"""

        try:
            response = self.sf_client.get_job_run(applicationId=app_id, jobRunId=run_id)
            job_run = EMRJobRunResponse(**response)
            return job_run.jobRun

        except Exception as e:
            error_message = f"Error getting run details of EMR Job run ID {run_id}: {e}"
            raise EMRManagerException(error_message)

    def list_job_runs(
        self, app_id: str, since_time: datetime, states: list[str] = []
    ) -> str:
        """List Job runs IDs submitted to the EMR Serverless application"""

        try:
            # paginator is used in order to attain the entire result set
            paginator = self.sf_client.get_paginator("list_job_runs")

            # paginate through results
            results_per_response = 50
            page_iterator = paginator.paginate(
                applicationId=app_id,
                createdAtAfter=since_time,
                states=states,  # if an empty list [] passed - all statuses will be considered
                PaginationConfig={
                    "PageSize": results_per_response,
                },
            )

            # collect all job run IDs returned
            runs_ids = [
                job["id"] for page in page_iterator for job in page.get("jobRuns", [])
            ]

            return runs_ids

        except Exception as e:
            error_message = f"Error getting a list of Job IDs submitted to the EMR application {app_id}: {e}"
            raise EMRManagerException(error_message)
