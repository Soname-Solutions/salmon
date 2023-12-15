import os
import boto3
import logging

from lib.aws.sts_manager import StsManager
from lib.aws.timestream_manager import TimestreamTableWriter
from lib.aws.aws_naming import AWSNaming
from lib.settings import Settings
from lib.core.constants import SettingConfigs

from lib.metrics_extractor import MetricsExtractorProvider

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sts_client = boto3.client("sts")
timestream_client = boto3.client("timestream-write")
timestream_query_client = boto3.client("timestream-query")


def get_service_client(account_id, region, role_name, aws_client_name):
    sts_manager = StsManager(sts_client)
    extract_metrics_role_arn = AWSNaming.Arn_IAMRole(None, account_id, role_name)

    try:
        client = sts_manager.get_client_via_assumed_role(
            aws_client_name=aws_client_name,
            via_assume_role_arn=extract_metrics_role_arn,
            region=region,
        )
        return client
    except Exception as ex:
        logger.error(f"Error while creating boto3 client: {str(ex)}")
        raise (ex)


def lambda_handler(event, context):
    logger.info(f"Event = {event}")

    # TODO: add a "semaphore" - if lambda works with a specific monitoring group, new invocation of lambda for the same monitoring group
    # doesn't proceed    

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]
    monitoring_group_name = event.get("monitoring_group")

    settings = Settings.from_s3_path(settings_s3_path)

    # getting content of the monitoring group (in pydantic class form)
    content = settings.get_monitoring_group_content(monitoring_group_name)

    for attr_name in content:
        attr_value = content[attr_name]
        # checking if it's our section like "glue_jobs", "lambda_functions" etc.
        if isinstance(attr_value, list) and attr_name in SettingConfigs.RESOURCE_TYPES:
            aws_service_name = attr_name
            aws_client_name = SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                attr_name
            ]
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
                    aws_client_name=aws_client_name,
                    role_name=iam_role_name,
                )
                
                # for local debugging:
                # aws_service_client = boto3.client(aws_client_name)

                metrics_table_name = AWSNaming.TimestreamTable(None, f"{aws_service_name}-metrics")

                timestream_man = TimestreamTableWriter(
                    db_name=timestream_metrics_db_name,
                    table_name=metrics_table_name,
                    timestream_write_client=timestream_client,
                )

                # 1. Create an extractor object for a specific service
                metrics_extractor = MetricsExtractorProvider.get_metrics_extractor(
                    service_name=aws_service_name,
                    aws_service_client=aws_service_client,
                    entity_name=entity_name,
                    monitored_environment_name=monitored_env,
                    timestream_db_name=timestream_metrics_db_name,
                    timestream_metrics_table_name=metrics_table_name,
                )
                logger.info(
                    f"Created metrics extractor of type {type(metrics_extractor)}"
                )

                # 2. Get time of this entity's data latest update (we append data since that time only)
                since_time = metrics_extractor.get_last_update_time(
                    timestream_query_client=timestream_query_client
                )
                if since_time is None:
                    since_time = timestream_man.get_earliest_writeable_time_for_table()
                print(f"Extracting metrics since {since_time}")

                # # 3. Extract metrics data in form of prepared list of timestream records
                records, common_attributes = metrics_extractor.prepare_metrics_data(
                    since_time=since_time
                )
                print(f"Extracted {len(records)} records")

                # # 4. Write extracted data to timestream table
                metrics_extractor.write_metrics(
                    records, common_attributes, timestream_table_writer=timestream_man
                )
                print(f"Written {len(records)} records to timestream")


if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)  # so we see logged messages in console when debugging

    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = "role-salmon-monitored-acc-extract-metrics-devam"
    os.environ[
        "TIMESTREAM_METRICS_DB_NAME"
    ] = "timestream-salmon-metrics-events-storage-devam"
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devam/settings/"

    #event = {'monitoring_group': 'salmonts_pyjobs'}
    #event = {"monitoring_group": "salmonts_workflows_sparkjobs"}
    event = {'monitoring_group': 'salmonts_lambdas_stepfunctions'}

    lambda_handler(event, None)
