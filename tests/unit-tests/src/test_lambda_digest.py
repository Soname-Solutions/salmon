import os
from datetime import datetime
from unittest.mock import patch, MagicMock, call
import pytest
from lambda_digest import (
    lambda_handler,
    extend_resources_config,
    group_recipients,
    append_digest_data,
    distribute_digest_report,
)
from lib.core.constants import SettingConfigs, DigestSettings
from lib.digest_service import SummaryEntry


STAGE_NAME = "teststage"


@pytest.fixture(scope="session")
def os_vars_init(aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    os.environ[
        "NOTIFICATION_QUEUE_URL"
    ] = f"https://sqs.{region}.amazonaws.com/{account_id}/queue-salmon-notification-{STAGE_NAME}.fifo"
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{STAGE_NAME}/settings/"
    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = f"role-salmon-monitored-acc-extract-metrics-{STAGE_NAME}"
    os.environ[
        "TIMESTREAM_METRICS_DB_NAME"
    ] = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    os.environ["DIGEST_REPORT_PERIOD_HOURS"] = "24"


#########################################################################################


@pytest.fixture(scope="module")
def mock_settings():
    def mocked_get_monitored_environment_props(monitored_env_name):
        props = {
            "Account1 [tests]": ("1111111111", "us-west-1"),
            "Account2 [tests]": ("2222222222", "us-east-2"),
        }
        return props.get(monitored_env_name, (None, None))

    def mocked_get_delivery_method(delivery_method_name):
        props = {
            "aws_ses": {
                "name": "aws_ses",
                "delivery_method_type": "AWS_SES",
                "sender_email": "admins@soname.de",
            },
            "local_smtp": {
                "name": "local_smtp",
                "delivery_method_type": "SMTP",
                "sender_email": "admins@soname.de",
                "credentials_secret_name": "sm-soname-smtp-server-creds",
            },
        }
        return props.get(delivery_method_name, {})

    with patch("lambda_digest.Settings") as mocked_settings:
        mocked_settings.get_monitoring_group_content.return_value = {"glue_jobs": {}}
        mocked_settings.get_monitoring_groups_by_resource_type.return_value = []
        mocked_settings.get_recipients_and_groups_by_notification_type.return_value = []

        mocked_settings.get_monitored_environment_props.side_effect = (
            mocked_get_monitored_environment_props
        )
        mocked_settings.get_delivery_method.side_effect = mocked_get_delivery_method
        yield mocked_settings


@pytest.fixture(scope="function", autouse=True)
def mock_send_messages_to_sqs():
    mocked_sqs_queue_sender = MagicMock()
    mocked_sqs_queue_sender.send_messages.return_value = {"result": "magic_mock"}
    with patch(
        "lambda_digest.SQSQueueSender", return_value=mocked_sqs_queue_sender
    ) as mock_sqs:
        yield mock_sqs


@pytest.fixture(scope="module", autouse=True)
def mock_digest_extractor():
    mock_extractor = MagicMock()
    with patch(
        "lambda_digest.DigestDataExtractorProvider.get_digest_provider",
        return_value=mock_extractor,
    ) as mock_instance:
        yield mock_instance, mock_extractor


#########################################################################################


def test_digest_lambda_handler(os_vars_init, mock_settings, mock_digest_extractor):
    lambda_handler({}, {})
    mock_instance, mock_extractor = mock_digest_extractor
    resource_types = SettingConfigs.RESOURCE_TYPES
    expected_calls = []
    for resource_type in resource_types:
        expected_calls.append(
            call(
                resource_type=resource_type,
                timestream_db_name=f"timestream-salmon-metrics-events-storage-{STAGE_NAME}",
                timestream_table_name=f"tstable-{resource_type}-metrics",
            )
        )

    # DigestDataExtractor called for each Resource Type
    mock_instance.assert_has_calls(expected_calls)
    assert mock_instance.call_count == len(resource_types)
    assert mock_extractor.extract_runs.call_count == len(resource_types)


@pytest.mark.parametrize(
    "scenario, recipients_groups, digest_data, expected_sqs_calles",
    [
        (
            "scen1",
            [
                {
                    "recipients": ["recipient1"],
                    "monitoring_groups": ["group1", "group2"],
                    "delivery_method": {},
                },
                {
                    "recipients": ["recipient2", "recipient3"],
                    "monitoring_groups": ["group4"],
                    "delivery_method": {},
                },
            ],
            [{"group1": {}}, {"group2": {}}],
            1,  # since no data for "group4", the message will not be sent
        ),
        (
            "scen2",
            [
                {
                    "recipients": ["recipient1"],
                    "monitoring_groups": ["group1", "group2"],
                    "delivery_method": {},
                },
                {
                    "recipients": ["recipient2", "recipient3"],
                    "monitoring_groups": ["group4"],
                    "delivery_method": {},
                },
            ],
            [{"group1": {}}, {"group4": {}}],
            2,
        ),
        (
            "scen3",
            [
                {
                    "recipients": ["recipient1"],
                    "monitoring_groups": ["group1", "group2"],
                    "delivery_method": {},
                },
                {
                    "recipients": ["recipient2", "recipient3"],
                    "monitoring_groups": ["group4"],
                    "delivery_method": {},
                },
                {
                    "recipients": ["recipient4"],
                    "monitoring_groups": ["group1"],
                    "delivery_method": {},
                },
            ],
            [{"group1": {}}, {"group2": {}}, {"group4": {}}],
            3,
        ),
    ],
)
def test_distribute_digest_report(
    mock_settings,
    mock_send_messages_to_sqs,
    scenario,
    recipients_groups,
    digest_data,
    expected_sqs_calles,
):
    digest_datetime = datetime(2000, 1, 1, 0, 0, 0)
    distribute_digest_report(
        recipients_groups=recipients_groups,
        digest_data=digest_data,
        digest_start_time=digest_datetime,
        digest_end_time=digest_datetime,
        notification_queue_url="test_url",
    )
    assert mock_send_messages_to_sqs.call_count == expected_sqs_calles


def test_append_digest_data(mock_settings):
    digest_data = []
    monitoring_groups = ["group1", "group2"]
    resource_type = "glue_jobs"
    extracted_runs = {}

    # Mock DigestDataAggregator calls
    aggregated_runs_mock = {}
    summary_mock = SummaryEntry(
        Executions=0, Success=0, Failures=0, Warnings=0, Status=DigestSettings.STATUS_OK
    )
    mock_aggregator = MagicMock()
    mock_aggregator.get_aggregated_runs.return_value = aggregated_runs_mock
    mock_aggregator.get_summary_entry.return_value = summary_mock

    with patch("lambda_digest.extend_resources_config") as mock_extend_resources_config:
        mock_extend_resources_config.return_value = {}
        append_digest_data(
            digest_data=digest_data,
            monitoring_groups=monitoring_groups,
            resource_type=resource_type,
            settings=mock_settings,
            extracted_runs=extracted_runs,
        )

    # Check that the data was appended as expected for each monitoring group
    expected_result = [
        {monitoring_groups[0]: {resource_type: {"runs": {}, "summary": summary_mock}}},
        {monitoring_groups[1]: {resource_type: {"runs": {}, "summary": summary_mock}}},
    ]
    print("digest_data ", digest_data)
    assert digest_data == expected_result
    assert len(digest_data) == len(monitoring_groups)


@pytest.mark.parametrize(
    "scenario, recipients, expected_recipients_groups",
    [
        (
            "scen1",
            [
                {
                    "recipient": "recipient1",
                    "delivery_method": "aws_ses",
                    "monitoring_groups": ["group1", "group2", "group3"],
                },
                {
                    "recipient": "recipient2",
                    "delivery_method": "local_smtp",
                    "monitoring_groups": ["group1"],
                },
                {
                    "recipient": "recipient3",
                    "delivery_method": "local_smtp",
                    "monitoring_groups": ["group1"],
                },
            ],
            {
                "aws_ses": ["recipient1"],
                "local_smtp": [
                    "recipient2",
                    "recipient3",
                ],  # since they share the same delivery method and list of monitoring groups
            },
        ),
        (
            "scen2",
            [
                {
                    "recipient": "recipient1",
                    "delivery_method": "aws_ses",
                    "monitoring_groups": ["group1", "group2", "group3"],
                },
                {
                    "recipient": "recipient2",
                    "delivery_method": "local_smtp",
                    "monitoring_groups": ["group1", "group2"],
                },
                {
                    "recipient": "recipient3",
                    "delivery_method": "aws_ses",
                    "monitoring_groups": ["group1", "group2", "group3"],
                },
            ],
            {
                "aws_ses": ["recipient1", "recipient3"],
                "local_smtp": ["recipient2"],
            },
        ),
    ],
)
def test_group_recipients(
    mock_settings, scenario, recipients, expected_recipients_groups
):
    result = group_recipients(recipients, mock_settings)

    actual_recipients_groups = {}
    for entry in result:
        delivery_method_name = entry["delivery_method"]["name"]
        recipients = entry["recipients"]
        actual_recipients_groups[delivery_method_name] = recipients

    assert actual_recipients_groups == expected_recipients_groups


@pytest.mark.parametrize(
    "scenario, resources_config, expected_extended_config",
    [
        (
            "scen_1",
            [
                {
                    "name": "glue-salmonts-pyjob-one-dev",
                    "monitored_environment_name": "Account1 [tests]",
                }
            ],
            [
                {
                    "name": "glue-salmonts-pyjob-one-dev",
                    "monitored_environment_name": "Account1 [tests]",
                    "account_id": "1111111111",
                    "region_name": "us-west-1",
                }
            ],
        ),
        (
            "scen_2",
            [
                {
                    "name": "glue-salmonts-two-dev2",
                    "monitored_environment_name": "Account2 [tests]",
                    "sla_seconds": 0,
                }
            ],
            [
                {
                    "name": "glue-salmonts-two-dev2",
                    "monitored_environment_name": "Account2 [tests]",
                    "sla_seconds": 0,
                    "account_id": "2222222222",
                    "region_name": "us-east-2",
                }
            ],
        ),
    ],
)
def test_extend_resources_config(
    mock_settings, scenario, resources_config, expected_extended_config
):
    actual_extended_config = extend_resources_config(mock_settings, resources_config)
    assert actual_extended_config == expected_extended_config
