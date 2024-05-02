import pytest
import os
import boto3
import json
from moto import mock_aws

from lib.settings import Settings, SettingsException
from lib.core.constants import DigestSettings
from unittest.mock import patch

from lib.core.constants import SettingConfigResourceTypes, NotificationType
import pytest

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
MOCKED_S3_BUCKET_NAME = "mocked_s3_config_bucket"

TOOLING_ACCOUNT_ID = "1234567890"
TOOLING_REGION = "us-east-1"

##############################################################################


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_setup(aws_credentials):
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=MOCKED_S3_BUCKET_NAME)

        # Path to your test configuration
        config_folder = os.path.join(CURRENT_FOLDER, "test_configs/config1/")

        # Upload files to the mocked S3 bucket
        for filename in os.listdir(config_folder):
            file_path = os.path.join(config_folder, filename)
            with open(file_path, "rb") as file_data:
                conn.upload_fileobj(file_data, MOCKED_S3_BUCKET_NAME, filename)

        yield


##############################################################################
# READ CONFIG TESTS


# testing reading config from local path (with minimal checks)
def test_read_from_path():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(config_path)

    tooling_account_props = settings.get_tooling_account_props()

    assert tooling_account_props == (
        TOOLING_ACCOUNT_ID,
        TOOLING_REGION,
    ), f"Tooling account properties doesn't match"


# testing reading config from mocked S3 bucket (with minimal checks)
def test_from_s3_path(s3_setup):
    config_path = f"s3://{MOCKED_S3_BUCKET_NAME}/"
    settings = Settings.from_s3_path(config_path)

    # Example of asserting the properties of the tooling account
    # Adjust the expected values according to the actual settings in 'config1'
    tooling_account_props = settings.get_tooling_account_props()
    assert tooling_account_props == (
        TOOLING_ACCOUNT_ID,
        TOOLING_REGION,
    ), f"Tooling account properties doesn't match"


# testing reading config without_replacements_file (shouldn't throw an error)
def test_read_from_path_without_replacements_file():
    config_path = os.path.join(
        CURRENT_FOLDER, "test_configs/config6_no_replacements_file/"
    )
    settings = Settings.from_file_path(config_path)

    tooling_account_props = settings.get_tooling_account_props()

    assert tooling_account_props == (
        TOOLING_ACCOUNT_ID,
        TOOLING_REGION,
    ), f"Tooling account properties doesn't match"


# testing reading config missing_recipients_file (SHOULD throw an error)
def test_read_from_path_missing_recipients_file():
    config_path = os.path.join(
        CURRENT_FOLDER, "test_configs/config7_missing_recipients_file/"
    )

    with pytest.raises(FileNotFoundError):
        settings = Settings.from_file_path(config_path)


##############################################################################
# GENERAL.JSON CONTENT TESTS


# tests getting general settings from config
def test_general_prop():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    general_settings = settings.general
    assert general_settings["tooling_environment"]["name"] == "Tooling Account [dev]"


def test_getting_tooling_env_props_when_explicitly_defined():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # in general -> tooling env we have (all defined EXPLICITLY, not using defaul values)
    expected_values = {
        "metrics_collection_interval_min": 10,
        "digest_report_period_hours": 48,
        "digest_cron_expression": "cron(5 8 * * ? *)",
        "grafana_instance": {
            "grafana_vpc_id": "vpc-123",
            "grafana_security_group_id": "sg-123",
        },
    }

    metrics_collection_interval_min = settings.get_metrics_collection_interval_min()
    digest_report_period_hours, digest_cron_expression = (
        settings.get_digest_report_settings()
    )
    (
        grafana_vpc_id,
        grafana_security_group_id,
        grafana_key_pair_name,
        grafana_bitnami_image,
        grafana_instance_type,
    ) = settings.get_grafana_settings()

    assert (
        metrics_collection_interval_min
        == expected_values["metrics_collection_interval_min"]
    )
    assert digest_report_period_hours == expected_values["digest_report_period_hours"]
    assert digest_cron_expression == expected_values["digest_cron_expression"]
    assert grafana_vpc_id == expected_values["grafana_instance"]["grafana_vpc_id"]
    assert (
        grafana_security_group_id
        == expected_values["grafana_instance"]["grafana_security_group_id"]
    )


def test_getting_tooling_env_props_when_omitted():
    config_path = os.path.join(
        CURRENT_FOLDER, "test_configs/config3_tooling_optional_props_omitted/"
    )
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # in general -> tooling env we have (all defined EXPLICITLY, not using defaul values)
    expected_values = {
        "metrics_collection_interval_min": 5,  # this one is mandatory anyway
        "digest_report_period_hours": DigestSettings.REPORT_PERIOD_HOURS,
        "digest_cron_expression": DigestSettings.CRON_EXPRESSION,
    }

    metrics_collection_interval_min = settings.get_metrics_collection_interval_min()
    digest_report_period_hours, digest_cron_expression = (
        settings.get_digest_report_settings()
    )
    grafana_settings = settings.get_grafana_settings()

    assert (
        metrics_collection_interval_min
        == expected_values["metrics_collection_interval_min"]
    )
    assert digest_report_period_hours == expected_values["digest_report_period_hours"]
    assert digest_cron_expression == expected_values["digest_cron_expression"]
    assert grafana_settings is None


# test getting a list of AWS account IDs where monitored environment exist
def test_monitored_account_info():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # in config there are 3 entries:
    # 1234567890 / eu-central-1,
    # 0987654321 / eu-central-1,
    # 1234567890 / us-west-2
    # it should deduplicate
    monitored_account_ids = settings.get_monitored_account_ids()

    assert len(monitored_account_ids) == 2, f"Unexpected number of monitored accounts"
    assert "1234567890" in monitored_account_ids
    assert "0987654321" in monitored_account_ids

    acc_region_pairs = settings.get_monitored_account_region_pairs()
    assert len(acc_region_pairs) == 3
    assert ("1234567890", "eu-central-1") in acc_region_pairs
    assert ("0987654321", "eu-central-1") in acc_region_pairs
    assert ("1234567890", "us-west-2") in acc_region_pairs


def test_get_monitored_environment_props():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # normal
    monitored_environment_name = "monitored3 [dev]"
    account_id, region = settings.get_monitored_environment_props(
        monitored_environment_name
    )

    assert account_id == "1234567890"
    assert region == "us-west-2"

    # non-existent env
    monitored_environment_name = "non-existent env"
    output = settings.get_monitored_environment_props(monitored_environment_name)
    assert output is None


def test_get_monitored_environment_name():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # normal
    account_id = "1234567890"
    region = "us-west-2"
    expected_monitored_environment_name = "monitored3 [dev]"
    monitored_environment_name = settings.get_monitored_environment_name(
        account_id=account_id, region=region
    )
    assert monitored_environment_name == expected_monitored_environment_name

    # non-existent env
    account_id = "7777777777"
    region = "us-west-2"
    output = settings.get_monitored_environment_name(
        account_id=account_id, region=region
    )
    assert output is None


##############################################################################
# MONITORING_GROUPS.JSON CONTENT TESTS


# tests working with monitoring groups
def test_monitoring_groups():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    monitoring_group_name = "group1"
    with patch(
        "lib.settings.Settings._get_all_resource_names",
        return_value={
            "glue_jobs": {"monitored1 [dev]": ["glue-job-1", "glue-job-2"]},
            "glue_workflows": {},
            "glue_crawlers": {},
            "glue_catalogs": {},
            "step_functions": {},
            "lambda_functions": {},
        },
    ):
        groups = settings.list_monitoring_groups()
        assert groups == ["group1"]

        content = settings.get_monitoring_group_content("group1")
        assert "glue_jobs" in content

        content = settings.get_monitoring_group_content("non_existent_group")
        assert content == {}


# tests getting raw monitoring groups config
def test_monitoring_groups_prop():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config2_wildcards/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    mon_gr_settings = settings.monitoring_groups

    content = mon_gr_settings.get("monitoring_groups", None)
    assert content is not None, f"monitoring_groups content is empty"

    glue_jobs_content = content[0].get("glue_jobs", None)
    assert glue_jobs_content is not None, f"glue_jobs content is empty"

    glue_job_name_wildcarded = glue_jobs_content[0]["name"]
    assert glue_job_name_wildcarded == "glue-job-*", f"glue_job name doesn't match"


# testing how defaults are applied to resources in monitoring groups (sla_seconds, minimum_number_of_runs)
def test_monitoring_group_resource_properties():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    monitoring_group_name = "group1"
    with patch(
        "lib.settings.Settings._get_all_resource_names",
        return_value={
            "glue_jobs": {
                "monitored1 [<<env>>]": [
                    "glue-job-1",
                    "glue-job-2",
                    "glue-job-3",
                    "glue-job-4",
                    "glue-job-5",
                ]
            },
            "glue_workflows": {},
            "glue_crawlers": {},
            "glue_catalogs": {},
            "step_functions": {},
            "lambda_functions": {},
        },
    ):
        content = settings.get_monitoring_group_content(monitoring_group_name)
        glue_jobs_content = content.get("glue_jobs", None)

        assert glue_jobs_content is not None, f"glue_jobs content is empty"
        assert len(glue_jobs_content) == 5, f"glue_jobs count doesn't match"

        expected_values = {
            "glue-job-1": {"sla_seconds": 0, "minimum_number_of_runs": 0},
            "glue-job-2": {"sla_seconds": 0, "minimum_number_of_runs": 0},
            "glue-job-3": {"sla_seconds": 100, "minimum_number_of_runs": 0},
            "glue-job-4": {"sla_seconds": 0, "minimum_number_of_runs": 0},
            "glue-job-5": {"sla_seconds": 0, "minimum_number_of_runs": 2},
        }
        for item in glue_jobs_content:
            job_name = item["name"]
            assert (
                item["sla_seconds"] == expected_values[job_name]["sla_seconds"]
            ), f"sla_seconds for {job_name} doesn't match"
            assert (
                item["minimum_number_of_runs"]
                == expected_values[job_name]["minimum_number_of_runs"]
            ), f"minimum_number_of_runs for {job_name} doesn't match"


# testing how wildcard replacements work
def test_monitoring_group_replace_wildcards():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config2_wildcards/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # in config2_wildcards we have definition of
    # glue-job-* (which should result in 2 entries)
    # "no-wild-card-job" (+1 entry, taken as is)

    monitoring_group_name = "group1"
    with patch(
        "lib.settings.Settings._get_all_resource_names",
        return_value={
            "glue_jobs": {
                "monitored1 [<<env>>]": [
                    "not-matching-job",
                    "nomatch-glue-job-1",
                    "glue-job-1",
                    "glue-job-2",
                    "no-wild-card-job",
                    "another-not-matching-job",
                ]
            },
            "glue_workflows": {},
            "glue_crawlers": {},
            "glue_catalogs": {},
            "step_functions": {},
            "lambda_functions": {},
        },
    ):
        content = settings.get_monitoring_group_content(monitoring_group_name)
        glue_jobs_content = content.get("glue_jobs", None)

        assert glue_jobs_content is not None, f"glue_jobs content is empty"
        assert len(glue_jobs_content) == 3, f"glue_jobs count doesn't match"

        glue_job_names = [item["name"] for item in glue_jobs_content]
        assert "glue-job-1" in glue_job_names, f"glue-job-1 not found"
        assert "glue-job-2" in glue_job_names, f"glue-job-2 not found"
        assert "no-wild-card-job" in glue_job_names, f"no-wild-card-job not found"


# test getting relevant groups by resource_name
def test_get_monitoring_groups():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config4_many_groups/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    with patch(
        "lib.settings.Settings._get_all_resource_names",
        return_value={
            "glue_jobs": {
                "monitored1 [<<env>>]": [
                    "glue-job-1",
                    "glue-job-2",
                ]
            },
            "glue_workflows": {
                "monitored1 [<<env>>]": [
                    "glue-workflow-1",
                    "glue-workflow-2",
                ]
            },
            "glue_crawlers": {},
            "glue_catalogs": {},
            "step_functions": {},
            "lambda_functions": {},
        },
    ):

        def assert_group_results(resulting_groups, expected_groups):
            assert len(resulting_groups) == len(expected_groups)
            for group in expected_groups:
                assert group in resulting_groups, f"group {group} not found"

        resource_name = "glue-job-1"
        expected_groups = ["group-all-glue", "group-glue-job-1"]
        groups = settings.get_monitoring_groups([resource_name])
        assert_group_results(groups, expected_groups)

        resource_name = "glue-workflow-1"
        expected_groups = ["group-all-glue", "group-glue-workflow-1"]
        groups = settings.get_monitoring_groups([resource_name])
        assert_group_results(groups, expected_groups)


# test getting relevant groups by resource_type
def test_get_monitoring_groups_by_resource_type():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config4_many_groups/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    with patch(
        "lib.settings.Settings._get_all_resource_names",
        return_value={
            "glue_jobs": {
                "monitored1 [<<env>>]": [
                    "glue-job-1",
                    "glue-job-2",
                ]
            },
            "glue_workflows": {
                "monitored1 [<<env>>]": [
                    "glue-workflow-1",
                    "glue-workflow-2",
                ]
            },
            "glue_crawlers": {},
            "glue_catalogs": {},
            "step_functions": {},
            "lambda_functions": {},
        },
    ):

        def assert_group_results(resulting_groups, expected_groups):
            assert len(resulting_groups) == len(expected_groups)
            for group in expected_groups:
                assert group in resulting_groups, f"group {group} not found"

        expected_groups = ["group-all-glue", "group-glue-job-1", "group-glue-job-2"]
        groups = settings.get_monitoring_groups_by_resource_type(
            SettingConfigResourceTypes.GLUE_JOBS
        )
        assert_group_results(groups, expected_groups)

        expected_groups = ["group-all-glue", "group-glue-workflow-1"]
        groups = settings.get_monitoring_groups_by_resource_type(
            SettingConfigResourceTypes.GLUE_WORKFLOWS
        )
        assert_group_results(groups, expected_groups)


def test_get_all_resource_names():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    glue_job_names = ["glue-job-1", "glue-job-2"]
    step_function_names = ["step-function-1", "step-function-2"]

    with patch("lib.aws.GlueManager.get_all_names", return_value=glue_job_names), patch(
        "lib.aws.StepFunctionsManager.get_all_names", return_value=step_function_names
    ), patch("lib.aws.StsManager.get_client_via_assumed_role"):

        result = settings._get_all_resource_names()

        assert SettingConfigResourceTypes.GLUE_JOBS in result
        assert SettingConfigResourceTypes.STEP_FUNCTIONS in result

        monitored_env_name = "monitored1 [dev]"
        assert (
            result[SettingConfigResourceTypes.GLUE_JOBS][monitored_env_name]
            == glue_job_names
        )
        assert (
            result[SettingConfigResourceTypes.STEP_FUNCTIONS][monitored_env_name]
            == step_function_names
        )


# should raise exception when no IAM role provided and still need to retrieve resources
def test_get_all_resource_names_no_iam_role():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(config_path)

    with pytest.raises(SettingsException, match="IAM Role"):
        settings._get_all_resource_names()


##############################################################################
# RECIPIENTS.JSON CONTENT TESTS


# tests getting recipients config
def test_recipients_prop():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    recipients_settings = settings.recipients
    content = recipients_settings.get("recipients", None)

    assert content is not None, f"recipients_settings content is empty"


def test_get_recipients():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config5_many_recipients/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    def assert_recipient_results(resulting_recipients, expected_recipients):
        assert len(resulting_recipients) == len(expected_recipients)
        got_recipients = [x["recipient"] for x in resulting_recipients]
        for recipient in expected_recipients:
            assert recipient in got_recipients, f"Recipient {recipient} not found"

    monitoring_groups = ["group1"]
    notification_type = NotificationType.ALERT
    expected_recipients = [
        "recipient_all@company.com",
        "recipient_group1_all@company.com",
    ]
    recipients = settings.get_recipients(
        monitoring_groups=monitoring_groups, notification_type=notification_type
    )
    assert_recipient_results(recipients, expected_recipients)

    monitoring_groups = ["group2"]
    notification_type = NotificationType.DIGEST
    expected_recipients = [
        "recipient_all@company.com",
        "recipient_group2_digest@company.com",
    ]
    recipients = settings.get_recipients(
        monitoring_groups=monitoring_groups, notification_type=notification_type
    )
    assert_recipient_results(recipients, expected_recipients)


def test_get_recipients_and_groups_by_notification_type():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config5_many_recipients/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    notification_type = NotificationType.DIGEST
    expected_recipients_and_subscriptions = {
        "recipient_all@company.com": ["group1", "group2"],
        "recipient_group1_all@company.com": ["group1"],
        "recipient_group2_alerts@company.com": [],
        "recipient_group2_digest@company.com": ["group2"],
        "recipient_empty@company.com": [],
        "recipient_all_false@company.com": [],
    }
    recipients = settings.get_recipients_and_groups_by_notification_type(
        notification_type=notification_type
    )

    assert len(recipients) == len(expected_recipients_and_subscriptions.keys())
    for recipient in recipients:
        recipient_key = recipient["recipient"]
        actual_groups = recipient["monitoring_groups"]

        expected_groups = expected_recipients_and_subscriptions[recipient_key]
        assert len(expected_groups) == len(actual_groups)
        for group in expected_groups:
            assert group in actual_groups, f"Group {group} not found"


def test_get_delivery_method():
    config_path = os.path.join(CURRENT_FOLDER, "test_configs/config5_many_recipients/")
    settings = Settings.from_file_path(
        config_path, iam_role_list_monitored_res="sample"
    )

    # 1. testing actual method
    delivery_method_name = "aws_ses"
    # taken from config5_many_recipients
    expected_result = {
        "name": "aws_ses",
        "delivery_method_type": "AWS_SES",
        "sender_email": "no-reply@company.com",
    }
    result = settings.get_delivery_method(delivery_method_name=delivery_method_name)

    assert result["name"] == expected_result["name"], f"name doesn't match"
    assert (
        result["delivery_method_type"] == expected_result["delivery_method_type"]
    ), f"delivery_method_type doesn't match"
    assert (
        result["sender_email"] == expected_result["sender_email"]
    ), f"sender_email doesn't match"

    # 2. testing non-existent method
    delivery_method_name = "random_method"
    result = settings.get_delivery_method(delivery_method_name=delivery_method_name)
    assert result == {}, f"result should be empty dict"
