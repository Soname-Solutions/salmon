import os
import json

from lib.core import json_utils as ju
from lib.settings.cdk.settings_validator import validate
from lib.settings import Settings


def test_settings_validation():
    """Test settings_validator.validate function"""
    test_settings_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(test_settings_dir, "../config/sample_settings/")
    settings = Settings.from_file_path(config_path)
    validate(settings)
    print("Settings validation passed")


def lambda_handler(event, context):
    """Test read from s3 and all the methods required for both CDK and lambdas"""
    settings_s3_bucket_name = os.environ.get("settings_s3_bucket_name")
    settings = Settings.from_s3_path(f"s3://{settings_s3_bucket_name}/settings/")

    event_data = ju.parse_json(event)
    job_name = event_data["detail"]["jobName"]

    # CDK methods
    print(f"Monitored account_ids: {settings.get_monitored_account_ids()}")
    print(
        f"Metrics collection interval (tooling env): {settings.get_metrics_collection_interval_min()}"
    )

    # Lambda methods
    account_id, region = "123456789", "eu-central-1"
    print(
        f"Monitored account name: {settings.get_monitored_environment_name(account_id, region)}"
    )
    monitoring_groups = settings.get_monitoring_groups([job_name])
    print(f"Monitoring groups for '{job_name}': {monitoring_groups}")
    print(f"Recipients list: {settings.get_recipients(monitoring_groups, 'alert')}")

    # Check processed settings
    print(json.dumps(settings.processed_settings, indent=4))


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

    test_settings_validation()
    lambda_handler(test_event, context)
