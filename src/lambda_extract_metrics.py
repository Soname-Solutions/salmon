from datetime import datetime
import os
from typing import Optional
import boto3
import json
from pydantic import BaseModel


from lib.aws.sts_manager import StsManager
from lib.aws.glue_manager import GlueManager
from lib.aws.aws_naming import AWSNaming
from lib.settings import Settings

sts_client = boto3.client('sts')

def get_service_client(account_id, service_name):
    role_name = os.environ['IAMROLE_MONITORED_ACC_EXTRACT_METRICS']
    sts_manager = StsManager(sts_client)
    extract_metrics_role_arn = AWSNaming.Arn_IAMRole(None,account_id,role_name)
    
    try:
        client = sts_manager.get_client_via_assumed_role(service_to_create_client_for=service_name, via_assume_role_arn=extract_metrics_role_arn)
        print('Client is created successfully')
        return client
    except Exception as ex:
        print(f'Error while creating boto3 client: {str(ex)}')
        raise(ex)    
       
def run_sample_code():
    account_id = '025590872641' # For now to demonstrate cross-account access
    role_name = os.environ['IAMROLE_MONITORED_ACC_EXTRACT_METRICS']
    current_service = 'glue'
    
    sts_manager = StsManager(sts_client)
    extract_metrics_role_arn = AWSNaming.Arn_IAMRole(None,account_id,role_name)
    
    try:
        client = sts_manager.get_client_via_assumed_role(service_to_create_client_for=current_service, via_assume_role_arn=extract_metrics_role_arn)
        print('Client is created successfully')
    except Exception as ex:
        print(f'Error while creating boto3 client: {str(ex)}')
        raise(ex)

    glue_manager = GlueManager(client)
    job_names = glue_manager.get_all_job_names()
    print(f"Existing Glue Jobs include: { ', '.join(job_names) }")

    return job_names


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

def lambda_handler(event, context):

    glue_job_name = "glue-salmonts-pyjob-one-dev"
    glue_client = boto3.client('glue')
    glue_manager = GlueManager(glue_client)
    
    response = glue_manager.get_job_runs(glue_job_name)    
    job_runs_data = JobRunsData.parse_obj(response)

    print(job_runs_data)


    # with open('response.txt', 'w') as f:
    #     f.write(str(response))


    # it is triggered by extract-metrics-orch(estration) lambda
    # in param = monitored env name

    # 1. gets from settings component:
    # - monitored_env settings (including metrics extraction role arn - even if it's implicit - by default)
    # - relevant monitoring_groups with settings

    # 2. iterates through all entries in monitoring_groups (glue jobs, lambdas, step functions etc.)
    # inside the cycle:

    # 2-1. get last update time from timestream table (dims: monitored_env, service_name, entity_name)

    # 2-2. creates object of class <service>MetricsExtractor, runs it providing last_update_time (so, collect metrics since then)
    # component returns records to be written into TimeStream

    # 2-3. writes metrics into TimeStream table related to specific AWS service (glue/lambda etc.)

    # 2-x. updates "last update time" for this entity (if success. "last_update_time" = for step 2-2)
    
    return {"message": "job_names"}


if __name__ == "__main__":
    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = "role-salmon-monitored-acc-extract-metrics-devam"
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devam/settings/"

    event = {"monitored_env": "devam", "service": "glue"}
    lambda_handler(event, None)