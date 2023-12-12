import os
import boto3
import logging

from lib.aws.sts_manager import StsManager
from lib.aws.glue_manager import GlueManager
from lib.aws.aws_naming import AWSNaming
from lib.settings import Settings
from lib.core.constants import SettingConfigs

from lib.metrics_extractor import MetricsExtractorProvider  # , BaseMetricsExtractor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sts_client = boto3.client("sts")


def get_service_client(account_id, region, role_name, aws_service_name):
    sts_manager = StsManager(sts_client)
    extract_metrics_role_arn = AWSNaming.Arn_IAMRole(None, account_id, role_name)

    try:
        client = sts_manager.get_client_via_assumed_role(
            aws_service_name=aws_service_name,
            via_assume_role_arn=extract_metrics_role_arn,
            region=region,
        )
        return client
    except Exception as ex:
        logger.error(f"Error while creating boto3 client: {str(ex)}")
        raise (ex)

def lambda_handler(event, context):
    print(event)

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    monitoring_group_name = event.get("monitoring_group")

    settings = Settings.from_s3_path(settings_s3_path)

    # getting content of the monitoring group (in pydantic class form)
    content = settings.get_monitoring_group_content(monitoring_group_name)

    for attr_name in content:
        attr_value = content[attr_name]
        # checking if it's our section like "glue_jobs", "lambda_functions" etc.
        if isinstance(attr_value, list) and attr_name in SettingConfigs.RESOURCE_TYPES:
            aws_service_name = attr_name
            print(f"Service name: {aws_service_name}")
            for item in attr_value:
                entity_name = item["name"]
                monitored_env = item["monitored_environment_name"]
                print(
                    f"Processing: {aws_service_name}: [{entity_name}] at env:{monitored_env}"
                )

                account_id, region = settings.get_monitored_environment_props(
                    monitored_env
                )

                aws_service_client = get_service_client(
                    account_id=account_id,
                    region=region,
                    aws_service_name=aws_service_name,
                    role_name=iam_role_name,
                )

                # MetricsExtractorProvider.get_metrics_extractor(service_name=aws_service_name,
                #                                                aws_service_client=aws_service_client,
                #                                                entity_name=entity_name,
                #                                                monitored_environment_name=monitored_env,
                #                                                timestream_db_name,
                #                                                timestream_metrics_table_name
                #                                                )

    return

    # glue_job_name = "glue-salmonts-pyjob-one-dev"
    # glue_client = boto3.client('glue')
    # glue_manager = GlueManager(glue_client)

    # response = glue_manager.get_job_runs(glue_job_name)
    # job_runs_data = JobRunsData.parse_obj(response)

    # print(job_runs_data)

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

    # TODO: add a "semaphore" - if lambda works with a specific monitoring group, new invocation of lambda for the same monitoring group
    # doesn't proceed

    return {"message": "job_names"}


if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)  # so we see logged messages in console when debugging

    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = "role-salmon-monitored-acc-extract-metrics-devam"
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devam/settings/"

    # event = {'monitoring_group': 'salmonts_pyjobs'}
    event = {"monitoring_group": "salmonts_workflows_sparkjobs"}

    lambda_handler(event, None)
