import os
from typing import Any
import boto3
import logging
from itertools import groupby

from lib.aws import AWSNaming, Boto3ClientCreator, TimestreamTableWriter
from lib.settings import Settings
from lib.core.constants import SettingConfigs

from lib.metrics_extractor import MetricsExtractorProvider
from lib.metrics_extractor.metrics_extractor_utils import get_last_update_time
from lib.core.constants import SettingConfigResourceTypes as types
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

timestream_client = boto3.client("timestream-write")
timestream_query_client = boto3.client("timestream-query")


def process_individual_resource(
    monitored_environment_name: str,
    resource_type: str,
    resource_name: str,
    boto3_client_creator: Boto3ClientCreator,
    aws_client_name: str,
    timestream_writer: TimestreamTableWriter,
    timestream_metrics_db_name: str,
    timestream_metrics_table_name: str,
    last_update_times: dict,
    alerts_event_bus_name: str,
):
    logger.info(
        f"Processing: {resource_type}: [{resource_name}] at env:{monitored_environment_name}"
    )

    # 1. Create an extractor object for a specific service
    metrics_extractor = MetricsExtractorProvider.get_metrics_extractor(
        resource_type=resource_type,
        boto3_client_creator=boto3_client_creator,
        aws_client_name=aws_client_name,
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
    metrics_record_count = len(records)
    logger.info(f"Extracted {metrics_record_count} records")

    # # 4. Write extracted data to timestream table
    metrics_extractor.write_metrics(
        records, common_attributes, timestream_table_writer=timestream_writer
    )
    logger.info(f"Written {metrics_record_count} records to timestream")

    # for resource types where alerts are processed inside Salmon (not by default EventBridge functionality)
    alerts_send = False
    if hasattr(metrics_extractor, "send_alerts"):
        logger.info(f"Sending alerts to event bus {alerts_event_bus_name}")
        account_id, region = (
            boto3_client_creator.account_id,
            boto3_client_creator.region,
        )
        metrics_extractor.send_alerts(alerts_event_bus_name, account_id, region)
        logger.info(f"Alerts have been sent successfully")
        alerts_send = True

    return {"metrics_records_written": metrics_record_count, "alerts_sent": alerts_send}


def process_all_resources_by_env_and_type(
    monitored_environment_name: str,
    resource_type: str,
    resource_names: list,
    settings: Settings,
    iam_role_name: str,
    timestream_metrics_db_name: str,
    last_update_times: dict,
    alerts_event_bus_name: str,
):
    logger.info(
        f"Processing resource type: {resource_type}, env: {monitored_environment_name}"
    )

    # 1. Create a Boto3ClientCreator for a specific service
    aws_client_name = SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[resource_type]
    account_id, region = settings.get_monitored_environment_props(
        monitored_environment_name
    )
    boto3_client_creator = Boto3ClientCreator(account_id, region, iam_role_name)

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
            boto3_client_creator=boto3_client_creator,
            aws_client_name=aws_client_name,
            timestream_writer=timestream_man,
            timestream_metrics_db_name=timestream_metrics_db_name,
            timestream_metrics_table_name=metrics_table_name,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
        )


def lambda_handler(event, context):
    logger.info(f"Event = {event}")

    # get vars from either ENV or Event
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]
    alerts_event_bus_name = os.environ["ALERTS_EVENT_BUS_NAME"]
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
                    alerts_event_bus_name=alerts_event_bus_name,
                )
