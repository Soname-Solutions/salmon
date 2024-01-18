import os
from typing import Any
import boto3
import logging
from itertools import groupby

from lib.aws.sts_manager import StsManager
from lib.aws.timestream_manager import TimestreamTableWriter
from lib.aws.aws_naming import AWSNaming
from lib.settings import Settings
from lib.core.constants import SettingConfigs

from lib.metrics_extractor import MetricsExtractorProvider
from lib.metrics_extractor.metrics_extractor_utils import get_last_update_time
import json

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
        logger.info(
            f"Created {aws_client_name} client, role: {extract_metrics_role_arn}"
        )
        return client
    except Exception as ex:
        logger.error(f"Error while creating boto3 client: {str(ex)}")
        raise (ex)


def process_individual_resource(
    monitored_environment_name: str,
    resource_type: str,
    resource_name: str,
    aws_service_client: Any,
    timestream_writer: TimestreamTableWriter,
    timestream_metrics_db_name: str,
    timestream_metrics_table_name: str,
    last_update_times: dict,
):
    logger.info(
        f"Processing: {resource_type}: [{resource_name}] at env:{monitored_environment_name}"
    )

    # 1. Create an extractor object for a specific service
    metrics_extractor = MetricsExtractorProvider.get_metrics_extractor(
        resource_type=resource_type,
        aws_service_client=aws_service_client,
        resource_name=resource_name,
        monitored_environment_name=monitored_environment_name,
        timestream_db_name=timestream_metrics_db_name,
        timestream_metrics_table_name=timestream_metrics_table_name,
    )
    logger.info(f"Created metrics extractor of type {type(metrics_extractor)}")

    # 2. Get time of this entity's data latest update (we append data since that time only)
    since_time = get_last_update_time(last_update_times, resource_type, resource_name)
    logger.info(
        f"Last update time (from payload) for {resource_type}[{resource_name}] = {since_time}"
    )

    if since_time is None:
        # if last_update_time was not given or missing - query for specific resource directly from table
        logger.info(
            f"No last_update_time for {resource_type}[{resource_name}] - querying directly from table"
        )
        since_time = metrics_extractor.get_last_update_time(
            timestream_query_client=timestream_query_client
        )

    if since_time is None:
        # if still there is no last_update_time - extract since time which Timestream is able to accept
        logger.info(
            f"No last_update_time for {resource_type}[{resource_name}] - querying from Timestream"
        )
        since_time = timestream_writer.get_earliest_writeable_time_for_table()
    logger.info(f"Extracting metrics since {since_time}")

    # # 3. Extract metrics data in form of prepared list of timestream records
    records, common_attributes = metrics_extractor.prepare_metrics_data(
        since_time=since_time
    )
    logger.info(f"Extracted {len(records)} records")

    # # 4. Write extracted data to timestream table
    metrics_extractor.write_metrics(
        records, common_attributes, timestream_table_writer=timestream_writer
    )
    logger.info(f"Written {len(records)} records to timestream")


def process_all_resources_by_env_and_type(
    monitored_environment_name: str,
    resource_type: str,
    resource_names: list,
    settings: Settings,
    iam_role_name: str,
    timestream_metrics_db_name: str,
    last_update_times: dict,
):
    logger.info(f"Processing resource type: {resource_type}, env: {monitored_environment_name}")

    # 1. Create a client for a specific service
    aws_client_name = SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[resource_type]
    account_id, region = settings.get_monitored_environment_props(
        monitored_environment_name
    )
    aws_service_client = get_service_client(
        account_id=account_id,
        region=region,
        aws_client_name=aws_client_name,
        role_name=iam_role_name,
    )

    # 2. Create a Timestream table writer for a specific service
    metrics_table_name = AWSNaming.TimestreamMetricsTable(None, resource_type)
    timestream_man = TimestreamTableWriter(
        db_name=timestream_metrics_db_name,
        table_name=metrics_table_name,
        timestream_write_client=timestream_client,
    )

    # 3. Process each resource of a specific type in a specific environment
    for name in resource_names:
        process_individual_resource(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_name=name,
            aws_service_client=aws_service_client,
            timestream_writer=timestream_man,
            timestream_metrics_db_name=timestream_metrics_db_name,
            timestream_metrics_table_name=metrics_table_name,
            last_update_times=last_update_times,
        )

def lambda_handler(event, context):
    logger.info(f"Event = {event}")

    # get vars from either ENV or Event
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]
    monitoring_group_name = event.get("monitoring_group")
    last_update_times = event.get("last_update_times")

    # getting content of the monitoring group (in pydantic class form)
    settings = Settings.from_s3_path(
        settings_s3_path, iam_role_list_monitored_res=iam_role_name
    )    
    content = settings.get_monitoring_group_content(monitoring_group_name)

    for attr_name in content:
        attr_value = content[attr_name]
        # checking if it's our section like "glue_jobs", "lambda_functions" etc.
        if isinstance(attr_value, list) and attr_name in SettingConfigs.RESOURCE_TYPES:
            resource_type = attr_name
            logger.info(f"Processing {resource_type}")

            data = attr_value
            # sorting so we can process resources optimally
            data.sort(key=lambda x: x["monitored_environment_name"])

            for monitored_environment_name, group in groupby(
                data, key=lambda x: x["monitored_environment_name"]
            ):
                resource_names = [item["name"] for item in group]

                process_all_resources_by_env_and_type(
                    monitored_environment_name=monitored_environment_name,
                    resource_type=resource_type,
                    resource_names=resource_names,
                    settings=settings,
                    iam_role_name=iam_role_name,
                    timestream_metrics_db_name=timestream_metrics_db_name,
                    last_update_times=last_update_times,
                )


if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)  # so we see logged messages in console when debugging

    timestream_metrics_db_name = "timestream-salmon-metrics-events-storage-devam"
    iam_role = "role-salmon-monitored-acc-extract-metrics-devam"
    s3_path = "s3://s3-salmon-settings-devam/settings/"

    os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"] = iam_role
    os.environ["TIMESTREAM_METRICS_DB_NAME"] = timestream_metrics_db_name
    os.environ["SETTINGS_S3_PATH"] = s3_path

    # adding last_update_times
    from lib.aws.timestream_manager import TimeStreamQueryRunner
    from lib.metrics_extractor import retrieve_last_update_time_for_all_resources

    timestream_query_client = boto3.client("timestream-query")
    query_runner = TimeStreamQueryRunner(timestream_query_client)
    last_update_times = retrieve_last_update_time_for_all_resources(
        query_runner, timestream_metrics_db_name, logger
    )

    monitoring_group = "salmonts_lambdas_stepfunctions"

    event = {
        "monitoring_group": monitoring_group,
        "last_update_times": last_update_times,
    }

    lambda_handler(event, None)
