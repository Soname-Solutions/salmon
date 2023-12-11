import boto3
from datetime import datetime

from pydantic import BaseModel
from typing import Optional


States_Success = ["SUCCEEDED"]
States_Failure = ["FAILED", "ERROR", "TIMEOUT", "STOPPED"]

class JobRun(BaseModel):
    Id: str
    Attempt: int
    TriggerName: str
    JobName: str
    StartedOn: datetime
    LastModifiedOn: datetime
    CompletedOn: datetime
    JobRunState: str
    ErrorMessage: Optional[str] = None
    PredecessorRuns: list[str] = []
    AllocatedCapacity: int
    ExecutionTime: int
    Timeout: int
    MaxCapacity: float
    LogGroupName: str
    GlueVersion: str

    @property
    def IsSuccess(self) -> bool:
        return self.JobRunState in States_Success
    
    @property
    def IsFailure(self) -> bool:
        return self.JobRunState in States_Failure

class JobRunsData(BaseModel):
    JobRuns: list[JobRun]
    NextToken: Optional[str] = None

class GlueManagerException(Exception):
    """Exception raised for errors encountered while running Glue client methods."""

    pass

class GlueManager:
    def __init__(self, glue_client=None):
        self.glue_client = boto3.client("glue") if glue_client is None else glue_client

    def get_all_job_names(self):
        try:
            response = self.glue_client.list_jobs()
            return response.get('JobNames')

        except Exception as e:
            error_message = f"Error getting list of glue jobs : {e}"
            raise GlueManagerException(error_message)            
        
    def get_job_runs(self, job_name: str, since_time: datetime) -> list[JobRun]:
        try:
            outp = []
            response = self.glue_client.get_job_runs(JobName=job_name)

            job_runs_data = JobRunsData.model_validate(response)
            outp = [x for x in job_runs_data.JobRuns if x.StartedOn >= since_time]

            return outp


        except Exception as e:
            error_message = f"Error getting glue job runs : {e}"
            raise GlueManagerException(error_message)

