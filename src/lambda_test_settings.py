import os
import json

from constants import SettingFileNames

from s3_manager import S3Manager
from settings.settings_reader import MonitoringSettingsReader, RecipientsSettingsReader


def lambda_handler(event, context):
    # Get environment variables
    settings_s3_bucket_name = os.environ.get("settings_s3_bucket_name")

    s3 = S3Manager()

    # Load setting files
    monitoring_group_settings = s3.read_settings_file(
        settings_s3_bucket_name, SettingFileNames.MONITORING_GROUPS_FILE_NAME
    )
    recipient_settings = s3.read_settings_file(
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
    event_data = json.loads(event)  # For testing, in future replaced with EventHandler
    monitoring_groups = (
        monitoring_settings_reader.get_monitoring_groups_by_resource_names(
            [event_data["detail"]["jobName"]]
        )
    )
    print(
        f"Monitoring groups for '{event_data['detail']['jobName']}': {monitoring_groups}"
    )

    # Get recipients list for a list of monitoring groups (with the specified notification type)
    notification_type = (
        "alert"  # For testing -> in future separate lambda functions for alert/digest?
    )
    recipients_list = (
        recipients_settings_reader.get_recipients_by_monitoring_groups_and_type(
            monitoring_groups, notification_type
        )
    )
    print(f"Recipients list for '{notification_type}': {recipients_list}")


if __name__ == "__main__":
    test_event = """
        {
            "version": "0",
            "id": "abcdef00-1234-5678-9abc-def012345678",
            "detail-type": "Glue Job State Change",
            "source": "aws.glue",
            "account": "123456789012",
            "time": "2017-09-07T18:57:21Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "jobName": "ds-source1-historical-data-load",
                "severity": "INFO",
                "state": "SUCCEEDED",
                "jobRunId": "jr_abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
                "message": "Job run succeeded"
            }
        }
        """
    context = ""
    lambda_handler(test_event, context)
