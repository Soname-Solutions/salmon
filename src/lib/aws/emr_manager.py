import boto3
import json
from datetime import datetime

from pydantic import BaseModel
from typing import Optional


################################################################
class SparkSubmit(BaseModel):
    # script location
    entryPoint: str


class JobDriver(BaseModel):
    sparkSubmit: Optional[SparkSubmit]


class EMRJobRunData(BaseModel):
    applicationId: str
    jobRunId: str
    name: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    state: str
    stateDetails: Optional[str] = None
    jobDriver: Optional[JobDriver] = None

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
    # FYI: all states = 'SUBMITTED'|'PENDING'|'SCHEDULED'|'RUNNING'|'SUCCESS'|'FAILED'|'CANCELLING'|'CANCELLED'

    def __init__(self, sf_client=None):
        self.sf_client = (
            boto3.client("emr-serverless") if sf_client is None else sf_client
        )

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        return state in cls.STATES_SUCCESS or state in cls.STATES_FAILURE

    def get_all_names(self, **kwargs):
        try:
            response = self.sf_client.list_applications()
            return [res["name"] for res in response.get("applications")]

        except Exception as e:
            error_message = f"Error getting list of EMR applications: {e}"
            raise EMRManagerException(error_message)

    def get_application_name(self, app_id: str) -> str:
        try:
            response = self.sf_client.get_application(applicationId=app_id)
            return response.get("application").get("name")

        except Exception as e:
            error_message = f"Error getting a name of EMR application ID {app_id}: {e}"
            raise EMRManagerException(error_message)

    def get_job_run(self, app_id: str, run_id: str) -> str:
        try:
            response = self.sf_client.get_job_run(applicationId=app_id, jobRunId=run_id)
            job_run = EMRJobRunResponse(**response)
            return job_run.jobRun

        except Exception as e:
            error_message = f"Error getting run details of EMR job run ID {run_id}: {e}"
            raise EMRManagerException(error_message)
