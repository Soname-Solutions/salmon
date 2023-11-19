import os
import sys

sys.path.append(os.getcwd())

import json

from lib.core import file_manager as fm
from lib.core import json_utils as ju
from lib.core.constants import SettingFileNames

from lib.aws import S3Manager
from lib.settings.settings_reader import (
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)
from lib.settings.settings_validator import validate


def test_settings_validation():
    """Test settings validation.

    This function performs both schema and business validation on the test settings.
    It reads the settings and schemas from specified paths, validates the JSON schemas,
    and then performs business validation using the validate function.

    Raises:
        jsonschema.exceptions.ValidationErro: If any schema validation checks fail.
        SettingsValidatorException: If any business validation checks fail.

    """
    schema_base_path = "schemas/"
    config_base_path = "../config/test_settings/"

    general = GeneralSettingsReader(
        SettingFileNames.GENERAL_FILE_NAME,
        fm.read_file(config_base_path + "general.json"),
    )
    monitoring_groups = MonitoringSettingsReader(
        SettingFileNames.MONITORING_GROUPS_FILE_NAME,
        fm.read_file(config_base_path + "monitoring_groups.json"),
    )
    recipients = RecipientsSettingsReader(
        SettingFileNames.RECIPIENTS_FILE_NAME,
        fm.read_file(config_base_path + "recipients.json"),
    )

    general_schema = ju.parse_json(fm.read_file(schema_base_path + "general.json"))
    monitoring_groups_schema = ju.parse_json(
        fm.read_file(schema_base_path + "monitoring_groups.json")
    )
    recipients_schema = ju.parse_json(
        fm.read_file(schema_base_path + "recipients.json")
    )

    # Schema validation
    print("Start General schema validation")
    ju.validate_json_schema(general.settings, general_schema)
    print("Start Monitoring Groups schema validation")
    ju.validate_json_schema(monitoring_groups.settings, monitoring_groups_schema)
    print("Start Recipients schema validation")
    ju.validate_json_schema(recipients.settings, recipients_schema)

    # Business validation
    print("Start business validation")
    validate(general, monitoring_groups, recipients)


def lambda_handler(event, context):
    """
    Lambda function to process event data, retrieve settings from an S3 bucket, and identify recipients based on monitoring groups.

    Args:
        event (object): Event data containing details about the AWS resource state change.
        context: (object): AWS Lambda context (not utilized in this function).

    Raises:
        S3ManagerReadException: If there is an error reading settings file from S3 bucket.
        ValueError: If the monitoring group settings or recipient settings are empty.

    Notes:
        - This function requires environment variable SETTINGS_S3_BUCKET_NAME to access S3 settings bucket.
        - It reads monitoring group and recipient settings files from S3.
        - Uses the provided event data to fetch monitoring groups and recipient details based on the AWS resource state change information.
        - Prints monitoring groups and recipient lists for testing purposes.

    """
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
    # lambda_handler(test_event, context)
    test_settings_validation()
