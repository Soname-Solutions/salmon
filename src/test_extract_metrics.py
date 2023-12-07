from datetime import datetime, timedelta
from typing import Optional

import boto3
import pytz
from pydantic import BaseModel

from lib.aws.glue_manager import GlueManager

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

class JobRunsData(BaseModel):
    JobRuns: list[JobRun]
    NextToken: Optional[str] = None

def glue_handler(event, context):

    glue_job_name = "glue-salmonts-pyjob-one-dev"
    glue_client = boto3.client('glue')
    glue_manager = GlueManager(glue_client)
    

    # Five hours prior to UTC current time
    since_time = datetime.now(tz=pytz.UTC) - timedelta(hours=5)

    response = glue_manager.get_job_runs(glue_job_name)    

    job_runs_data = JobRunsData.model_validate(response)
    job_runs_data.JobRuns = [x for x in job_runs_data.JobRuns if x.StartedOn >= since_time]

    print(job_runs_data.model_dump_json(indent=4))
    #print(job_runs_data)


if __name__ == "__main__":
    glue_handler(None, None)    