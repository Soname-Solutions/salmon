import os
import json
import logging

import boto3
from lib.settings import Settings
from lib.metrics_storage.timestream_metrics_storage import TimestreamMetricsStorage

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    # Load environment variables
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    lambda_extract_metrics_name = os.environ["LAMBDA_EXTRACT_METRICS_NAME"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]

    # Step 1: Retrieve settings and list monitoring groups
    settings = Settings.from_s3_path(settings_s3_path)
    monitoring_groups = settings.list_monitoring_groups()

    # Step 2: Initialize TimestreamMetricsStorage and retrieve last update times
    timestream_storage = TimestreamMetricsStorage(db_name=timestream_metrics_db_name)
    last_update_times = timestream_storage.retrieve_last_update_time_for_all_resources(
        logger
    )
    logger.info(f"Last Update Times: {last_update_times}")

    # Step 3: Iterate through monitoring groups and invoke metrics extraction Lambda
    for monitoring_group in monitoring_groups:
        logger.info(f"Processing {monitoring_group}")

        # Asynchronously invoke extract-metrics Lambda function
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
