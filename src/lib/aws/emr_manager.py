import boto3
import json
from datetime import datetime

from pydantic import BaseModel
from typing import Optional


################################################################
class ExecutionData(BaseModel):
    applicationId: str
    id: str
    name: str
    mode: str
    arn: str
    state: str
    stateDetails: str
    type: str
    attemptCreatedAt: datetime
    attemptUpdatedAt: Optional[datetime]

    @property
    def IsSuccess(self) -> bool:
        return self.state in EMRManager.STATES_SUCCESS

    @property
    def IsFailure(self) -> bool:
        return self.state in EMRManager.STATES_FAILURE


class EMRExecutionsData(BaseModel):
    executions: list[ExecutionData]
    nextToken: Optional[str]


################################################################


class EMRManagerException(Exception):
    """Exception raised for errors encountered while running EMR client methods."""

    pass


class EMRManager:
    STATES_SUCCESS = ["SUCCESS"]
    STATES_FAILURE = ["FAILED", "CANCELLED"]
    # FYI: all states = 'SUBMITTED'|'PENDING'|'SCHEDULED'|'RUNNING'|'SUCCESS'|'FAILED'|'CANCELLING'|'CANCELLED'

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        return state in cls.STATES_SUCCESS or state in cls.STATES_FAILURE

    def __init__(self, sf_client=None):
        self.sf_client = (
            boto3.client("emr-serverless") if sf_client is None else sf_client
        )

    def get_all_names(self, **kwargs):
        try:
            response = self.sf_client.list_job_runs()
            return [res["name"] for res in response.get("jobRuns")]

        except Exception as e:
            error_message = f"Error getting list of EMR job runs: {e}"
            raise EMRManagerException(error_message)
