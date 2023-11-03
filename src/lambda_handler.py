import os

from constants import SettingFileNames

from s3_manager import S3Manager
from settings.settings_reader import (
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)


def lambda_handler(event, context):
    # Get environment variables
    settings_s3_bucket_name = os.environ.get("settings_s3_bucket_name")

    s3 = S3Manager()

    # Load setting files
    monitoring_group_settings = s3.download_settings_file(
        settings_s3_bucket_name, SettingFileNames.MONITORING_GROUPS_FILE_NAME
    )
    recipient_settings = s3.download_settings_file(
        settings_s3_bucket_name, SettingFileNames.RECIPIENTS_FILE_NAME
    )

    if not monitoring_group_settings:
        raise ValueError(
            f"Settings file {SettingFileNames.MONITORING_GROUPS_FILE_NAME} is empty"
        )
    elif not recipient_settings:
        raise ValueError(
            f"Settings file {SettingFileNames.RECIPIENTS_FILE_NAME} is empty"
        )

    monitoring_settings_reader = MonitoringSettingsReader(
        SettingFileNames.MONITORING_GROUPS_FILE_NAME, monitoring_group_settings
    )
    recipients_settings_reader = RecipientsSettingsReader(
        SettingFileNames.RECIPIENTS_FILE_NAME, recipient_settings
    )

    # Get monitoring groups for a specific glue job/lambda function
    glue_job_name = "ds-source1-historical-data-load"  # For testing -> in future retrieved from event input param
    monitoring_groups = monitoring_settings_reader.get_monitoring_groups_by_resource_names(
        [glue_job_name]
    )
    print(f"Monitoring groups for '{glue_job_name}': {monitoring_groups}")

    # Get recipients list for a list of monitoring groups (with the specified notification type)
    notification_type = (
        "alert"  # For testing -> in future separate lambda functions for alert/digest?
    )
    recipients_list = recipients_settings_reader.get_recipients_by_monitoring_groups_and_type(
        monitoring_groups, notification_type
    )
    print(f"Recipients list for '{notification_type}': {recipients_list}")
