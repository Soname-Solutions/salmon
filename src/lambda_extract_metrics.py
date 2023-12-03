import os
import boto3
import json

from lib.aws.sts_manager import StsManager
from lib.aws.glue_manager import GlueManager
from lib.aws.aws_naming import AWSNaming

sts_client = boto3.client('sts')


def run_sample_code():
    account_id = '405389362913' # map to value from event
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


def lambda_handler(event, context):
    
    # just a sample code to test and demonstrate functionality
    # it's here temporarily
    job_names = run_sample_code()    


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
    
    return {"message": job_names}
