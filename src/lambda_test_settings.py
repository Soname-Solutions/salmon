import os
import json

from lib.core import json_utils as ju
from lib.core.constants import NotificationType
from lib.settings import Settings


def lambda_handler(event, context):
    """Test read from s3 and all the methods required for both CDK and lambdas"""
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]

    settings = Settings.from_s3_path(settings_s3_path, iam_role_name)

    job_name = event["detail"]["jobName"]

    # CDK methods
    print(f"Monitored account_ids: {settings.get_monitored_account_ids()}")
    print(
        f"Metrics collection interval (tooling env): {settings.get_metrics_collection_interval_min()}"
    )

    # Lambda methods
    account_id, region = "405389362913", "eu-central-1"
    print(
        f"Monitored account name: {settings.get_monitored_environment_name(account_id, region)}"
    )
    monitoring_groups = settings.get_monitoring_groups([job_name])
    print(f"Monitoring groups for '{job_name}': {monitoring_groups}")
    print(
        f"Recipients list: {settings.get_recipients(monitoring_groups, NotificationType.ALERT)}"
    )

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
                "jobName": "glue-salmonts-sparkjob-two-dev2",
                "severity": "INFO",
                "state": "SUCCEEDED",
                "jobRunId": "jr_abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
                "message": "Job run succeeded"
            }
        }
        """
    context = ""

    lambda_handler(ju.parse_json(test_event), context)
