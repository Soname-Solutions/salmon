import os
import logging
from datetime import datetime, timedelta, timezone
import boto3

from lib.core.constants import SettingConfigs, NotificationType
from lib.aws.aws_naming import AWSNaming
from lib.aws.sqs_manager import SQSQueueSender
from lib.settings.settings import Settings
from lib.digest_service import (
    DigestDataAggregator,
    DigestDataExtractorProvider,
    DigestMessageBuilder,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client("lambda")
sqs_client = boto3.client("sqs")


def extend_resources_config(settings: Settings, configs: dict) -> list:
    """
    Extends the resources configs with the account id and region name
    (required for job run url).
    """
    extended_config = []

    for config in configs:
        monitored_env_name = config.get("monitored_environment_name")

        if monitored_env_name:
            account_id, region_name = settings.get_monitored_environment_props(
                monitored_env_name
            )
            config["account_id"] = account_id
            config["region_name"] = region_name
            extended_config.append(config)

    return extended_config


def group_recipients(recipients: list, settings: Settings) -> list:
    """
    Groups recipients with the same delivery method name and the same set of
    the monitoring groups with the digest option enabled.
    """
    grouped_recipients = {}

    for recipient in recipients:
        key = (
            recipient["delivery_method"],
            tuple(sorted(recipient["monitoring_groups"])),
        )
        if key not in grouped_recipients:
            grouped_recipients[key] = {
                "recipients": [],
                "delivery_method": settings.get_delivery_method_options(
                    recipient["delivery_method"]
                ),
                "monitoring_groups": recipient["monitoring_groups"],
            }
        grouped_recipients[key]["recipients"].append(recipient["recipient"])

    return list(grouped_recipients.values())


def append_digest_data(
    digest_data: list,
    monitoring_groups: list,
    resource_type: str,
    settings: Settings,
    extracted_runs: dict,
):
    """
    For each monitoring group and resource type, an item is added to the digest list.
    Sample output:
    {
        "salmonts_workflows_sparkjobs": {
            "glue_jobs": {
                "runs": {
                    "glue-salmonts-sparkjob-one-dev": { "Status": "ok", "Executions": 2, "Failures": 0,
                             "values": { "Success": 2, "Errors": 0, "Warnings": 0, "Comments": "" },
                    }, ...
                },
                "summary": { "Status": "ok", "Executions": 2, "Success": 2, "Failures": 0, "Warnings": 0 },
            }
        }
    }
    """
    for monitoring_group in monitoring_groups:
        logger.info(
            f"Processing {resource_type} for the monitoring group: {monitoring_group}"
        )
        monitoring_group_config = settings.get_monitoring_group_content(
            monitoring_group
        )
        resources_config = extend_resources_config(
            settings, monitoring_group_config[resource_type]
        )
        digest_aggregator = DigestDataAggregator()
        aggregated_runs = digest_aggregator.get_aggregated_runs(
            extracted_runs, resources_config, resource_type
        )
        summary = digest_aggregator.get_summary_entry(aggregated_runs)
        digest_data.append(
            {
                monitoring_group: {
                    resource_type: {"runs": aggregated_runs, "summary": summary}
                }
            }
        )


def distribute_digest_report(
    recipients_groups: list,
    digest_data: list,
    digest_start_time: datetime,
    digest_end_time: datetime,
    notification_queue_url: str,
):
    logger.info("Distributing the digest report to the relevant recipients")

    for recipients_group in recipients_groups:
        # get relevant digest data
        recipients_group_data = [
            item
            for item in digest_data
            if next(iter(item.keys())) in recipients_group["monitoring_groups"]
        ]

        if recipients_group_data:
            # prepare the digest message
            message_builder = DigestMessageBuilder(recipients_group_data)
            message_body = message_builder.generate_message_body(
                digest_start_time, digest_end_time
            )
            message = {
                "delivery_options": {
                    "recipients": recipients_group["recipients"],
                    "delivery_method": recipients_group["delivery_method"],
                },
                "message": {
                    "message_subject": f"Digest Report {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}",
                    "message_body": message_body,
                },
            }
            sender = SQSQueueSender(notification_queue_url, sqs_client)
            results = sender.send_messages([message])

            logger.info(
                f"Results of sending messages to SQS: {results} for the recipient group: {recipients_group['recipients']}"
            )


def lambda_handler(event, context):
    # it is triggered based on the cron schedule set in the config
    logger.info(f"event = {event}")

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    notification_queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]
    report_period_hours = int(os.environ["DIGEST_REPORT_PERIOD_HOURS"])
    settings = Settings.from_s3_path(
        base_path=settings_s3_path, iam_role_list_monitored_res=iam_role_name
    )

    digest_end_time = datetime.now(tz=timezone.utc)
    digest_start_time = digest_end_time - timedelta(hours=report_period_hours)

    # prepare digest data
    digest_data = []
    metric_table_names = {
        x: AWSNaming.TimestreamMetricsTable(None, x)
        for x in SettingConfigs.RESOURCE_TYPES
    }
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        # ceate an digest extractor for a specific resource type
        digest_extractor = DigestDataExtractorProvider.get_digest_provider(
            resource_type=resource_type,
            timestream_db_name=timestream_metrics_db_name,
            timestream_table_name=metric_table_names[resource_type],
        )
        logger.info(f"Created digest extractor of type {type(digest_extractor)}")
        query = digest_extractor.get_query(digest_start_time, digest_end_time)
        extracted_runs = digest_extractor.extract_runs(query)

        # aggregate runs per monitoring_group and resource_type
        monitoring_groups = settings.get_monitoring_groups_by_resource_type(
            resource_type=resource_type
        )
        append_digest_data(
            digest_data=digest_data,
            monitoring_groups=monitoring_groups,
            resource_type=resource_type,
            settings=settings,
            extracted_runs=extracted_runs,
        )
    # sort data by monitoring group name
    digest_data = sorted(digest_data, key=lambda x: next(iter(x.keys())))

    # get and group recipients
    recipients = settings.get_recipients_and_groups_by_notification_type(
        NotificationType.DIGEST
    )
    recipients_groups = group_recipients(recipients, settings)

    # send the digest report to each recipients group
    distribute_digest_report(
        recipients_groups=recipients_groups,
        digest_data=digest_data,
        digest_start_time=digest_start_time,
        digest_end_time=digest_end_time,
        notification_queue_url=notification_queue_url,
    )


if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = "role-salmon-monitored-acc-extract-metrics-devay"
    os.environ[
        "TIMESTREAM_METRICS_DB_NAME"
    ] = "timestream-salmon-metrics-events-storage-devay"
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devay/settings/"
    os.environ["DIGEST_REPORT_PERIOD_HOURS"] = "24"
    os.environ[
        "NOTIFICATION_QUEUE_URL"
    ] = "https://sqs.{region}.amazonaws.com/{account_id}/queue-salmon-notification-devay"

    event = {}
    lambda_handler(event, None)
