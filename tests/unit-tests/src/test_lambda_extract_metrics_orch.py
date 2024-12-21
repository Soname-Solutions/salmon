import pytest
import os
import json
import boto3

from moto import mock_aws
from lambda_extract_metrics_orch import lambda_handler
from unittest.mock import patch, call

from lib.settings.settings import Settings

# uncomment this to see lambda's logging output
# import logging

# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# logger.addHandler(handler)

LAST_UPDATE_TIMES_SAMPLE = {
    "glue_jobs": [
        {
            "resource_name": "glue-job1",
            "last_update_time": "2024-04-16 12:05:11.275000000",
        },
        {
            "resource_name": "glue-job2",
            "last_update_time": "2024-04-16 11:05:11.275000000",
        },
    ],
    "step_functions": [
        {
            "resource_name": "step-function1",
            "last_update_time": "2024-04-16 12:05:11.275000000",
        },
        {
            "resource_name": "step-function2",
            "last_update_time": "2024-04-16 11:05:11.275000000",
        },
    ],
}
#########################################################################################


@pytest.fixture(scope="module", autouse=True)
def os_vars_init(aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    stage_name = "teststage"
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ[
        "LAMBDA_EXTRACT_METRICS_NAME"
    ] = f"lambda-salmon-extract-metrics-{stage_name}"
    os.environ[
        "TIMESTREAM_METRICS_DB_NAME"
    ] = f"timestream-salmon-metrics-events-storage-{stage_name}"


#########################################################################################


@pytest.fixture(scope="module", autouse=True)
def mock_settings(config_path_main_tests):
    """
    A module-scoped fixture that automatically mocks Settings.from_s3_path
    to call Settings.from_file_path with a predetermined local path for all tests.
    """
    with patch(
        "lambda_alerting.Settings.from_s3_path",
        side_effect=lambda x: Settings.from_file_path(config_path_main_tests),
    ) as _mock:
        yield _mock


@pytest.fixture(scope="function")
def mock_lambda_invoke():
    with patch(
        "lambda_extract_metrics_orch.lambda_client.invoke", return_value="test_mock"
    ) as _mock:
        yield _mock


@pytest.fixture(scope="module")
def mock_last_update_times():
    with patch(
        "lambda_extract_metrics_orch.TimestreamMetricsStorage.retrieve_last_update_time_for_all_resources",
        return_value=LAST_UPDATE_TIMES_SAMPLE,
    ) as _mock:
        yield _mock


#########################################################################################
def test_lambda_handler(mock_settings, mock_lambda_invoke, mock_last_update_times):
    monitoring_groups = ["test_group1", "test_group2"]
    with patch(
        "lambda_extract_metrics_orch.Settings.list_monitoring_groups",
        return_value=monitoring_groups,
    ) as mock_get_monitoring_group:
        lambda_handler({}, {})

    lambda_name = os.environ["LAMBDA_EXTRACT_METRICS_NAME"]

    expected_calls = []
    for group in monitoring_groups:
        expected_calls.append(
            call(
                FunctionName=lambda_name,
                InvocationType="Event",
                Payload=json.dumps(
                    {
                        "monitoring_group": group,
                        "last_update_times": LAST_UPDATE_TIMES_SAMPLE,
                    }
                ),
            )
        )

    mock_lambda_invoke.assert_has_calls(expected_calls)


def test_lambda_handler_no_groups(
    mock_settings, mock_lambda_invoke, mock_last_update_times
):
    monitoring_groups = []
    with patch(
        "lambda_extract_metrics_orch.Settings.list_monitoring_groups",
        return_value=monitoring_groups,
    ) as mock_get_monitoring_group:
        lambda_handler({}, {})

    mock_lambda_invoke.assert_not_called()
