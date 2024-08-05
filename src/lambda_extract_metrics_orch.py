import os
import json
import logging

from lib.settings import Settings
import boto3

from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.metrics_extractor import retrieve_last_update_time_for_all_resources

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    # it is triggered once in <x> minutes by eventbridge schedule rule
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    lambda_extract_metrics_name = os.environ["LAMBDA_EXTRACT_METRICS_NAME"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]

    # 1. ask settings for all "monitoring_groups"
    settings = Settings.from_s3_path(settings_s3_path)

    monitoring_groups = settings.list_monitoring_groups()

    # 2. collect last_update time for all resources
    timestream_query_client = boto3.client("timestream-query")
    query_runner = TimeStreamQueryRunner(timestream_query_client)
    last_update_times = retrieve_last_update_time_for_all_resources(
        query_runner, timestream_metrics_db_name, logger
    )
    logger.info(f"Last Update Times : {last_update_times}")

    # 3. iterates through "monitoring_groups"
    for monitoring_group in monitoring_groups:
        logger.info(f"Processing {monitoring_group}")

        # foreach - 3a. invokes (async) extract-metrics lambda (params = "monitored_environment" name)
        lambda_client.invoke(
            FunctionName=lambda_extract_metrics_name,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "monitoring_group": monitoring_group,
                    "last_update_times": last_update_times,
                }
            ),
        )
        logger.info(
            f"Invoked lambda {lambda_extract_metrics_name} for monitoring group: {monitoring_group}"
        )
