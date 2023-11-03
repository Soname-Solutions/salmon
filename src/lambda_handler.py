import os

from constants import AWSResources, SettingFileNames

from s3_manager import S3Manager
from settings_component.settings_reader import (
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)


def lambda_handler(event, context):
    # Get environment variables
    project_name = os.environ.get("project_name")
    stage_name = os.environ.get("stage_name")

    s3 = S3Manager()

    # Load setting files
    monitoring_group_settings = s3.download_settings_file(
        f"s3-{project_name}-settings-{stage_name}", SettingFileNames.MONITORING_GROUPS_FILE_NAME
    )
    recipient_settings = s3.download_settings_file(
        f"s3-{project_name}-settings-{stage_name}", SettingFileNames.RECIPIENTS_FILE_NAME
    )

    if not monitoring_group_settings:
        raise ValueError(
            f"Settings file {SettingFileNames.MONITORING_GROUPS_FILE_NAME} is empty"
        )
    elif not recipient_settings:
        raise ValueError(
            f"Settings file {SettingFileNames.RECIPIENTS_FILE_NAME} is empty"
        )

    monitoring_settings_reader = MonitoringSettingsReader(monitoring_group_settings)
    recipients_settings_reader = RecipientsSettingsReader(recipient_settings)

    # Get monitoring groups for a specific glue job/lambda function
    glue_job_name = "ds-source1-historical-data-load"  # For testing -> in future retrieved from event input param
    monitoring_groups = monitoring_settings_reader.get_monitoring_groups_by_name(
        glue_job_name
    )
    print(f"Monitoring groups for '{glue_job_name}': {monitoring_groups}")

    # Get recipients list for a list of monitoring groups (with the specified notification type)
    notification_type = (
        "alert"  # For testing -> in future separate lambda functions for alert/digest
    )
    recipients_list = recipients_settings_reader.get_recipients_for_monitoring_groups(
        monitoring_groups, notification_type
    )
    print(f"Recipients list for '{notification_type}':")
    for recipient in recipients_list:
        print(
            f"- Recipient: {recipient['recipient']}, Delivery Method: {recipient['delivery_method']}"
        )
