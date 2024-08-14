import boto3
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional


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

        # trim the message to 200 chars, adding '...' if it exceeds this length
        return (
            (error_message[:200] + "...") if len(error_message) > 200 else error_message
        )


class EMRJobRunResponse(BaseModel):
    jobRun: EMRJobRunData


################################################################


class EMRManagerException(Exception):
    """Exception raised for errors encountered while running EMR client methods."""

    pass


class EMRManager:
    STATES_SUCCESS = ["SUCCESS"]
    STATES_FAILURE = ["FAILED", "CANCELLED"]
    ALL_STATES = [
        "SUBMITTED",
        "PENDING",
        "SCHEDULED",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "CANCELLING",
        "CANCELLED",
    ]

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
            if not states:
                states = self.ALL_STATES

            response = self.sf_client.list_job_runs(
                applicationId=app_id, createdAtAfter=since_time, states=states
            )
            outp = [x["id"] for x in response.get("jobRuns")]
            return outp

        except Exception as e:
            error_message = f"Error getting a list of Job IDs submitted to the EMR application {app_id}: {e}"
            raise EMRManagerException(error_message)
