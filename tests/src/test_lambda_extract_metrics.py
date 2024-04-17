import pytest
import os
import json
import boto3

from moto import mock_aws
from lambda_extract_metrics import lambda_handler
from unittest.mock import patch, call, MagicMock, ANY

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
    os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"] = (
        f"role-salmon-monitored-acc-extract-metrics-{stage_name}"
    )
    os.environ["TIMESTREAM_METRICS_DB_NAME"] = (
        f"timestream-salmon-metrics-events-storage-{stage_name}"
    )
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ["ALERTS_EVENT_BUS_NAME"] = f"eventbus-salmon-alerting-{stage_name}"


#########################################################################################


class MockedSettings:
    @classmethod
    def from_s3_path(cls, base_path: str, iam_role_list_monitored_res: str = None):
        return MockedSettings()

    def get_monitoring_group_content(self, group_name: str) -> dict:
        return {"content": "define in a specific test"}


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lambda_extract_metrics.Settings", MockedSettings) as mocked_setting:
        yield MockedSettings


@pytest.fixture(scope="function")
def mock_process_all_resources_by_env_and_type():
    with patch(
        "lambda_extract_metrics.process_all_resources_by_env_and_type"
    ) as mocked_function:
        yield mocked_function


#########################################################################################

def test_lambda_handler_empty_group_content(
    os_vars_init, mock_settings, mock_process_all_resources_by_env_and_type
):
    monitoring_group = "group1"
    event = {
        "monitoring_group": monitoring_group,
        "last_update_times": LAST_UPDATE_TIMES_SAMPLE,
    }

    # checking no calls to process_all_resources_by_env_and_type made and no lambda failure
    group_context = {}

    with patch(
        "test_lambda_extract_metrics.MockedSettings.get_monitoring_group_content",
        return_value=group_context,
    ):
        lambda_handler(event, None)

    mock_process_all_resources_by_env_and_type.assert_not_called()


def test_lambda_handler_with_group_content(
    os_vars_init, mock_settings, mock_process_all_resources_by_env_and_type
):
    monitoring_group = "group1"
    event = {
        "monitoring_group": monitoring_group,
        "last_update_times": LAST_UPDATE_TIMES_SAMPLE,
    }

    # checking calls to process_all_resources_by_env_and_type are made in a specific order
    # and resources are grouped properly (by env and resource type)
    group_context = {
        "group_name": "salmonts_workflows_sparkjobs",
        "glue_jobs": [
            {"name": "glue_job1", "monitored_environment_name": "env1"},
            {"name": "glue_job2", "monitored_environment_name": "env2"},
            {"name": "glue_job3", "monitored_environment_name": "env1"},
        ],
        "glue_workflows": [
            {"name": "glue_workflow1", "monitored_environment_name": "env1"}
        ],
    }

    with patch(
        "test_lambda_extract_metrics.MockedSettings.get_monitoring_group_content",
        return_value=group_context,
    ):
        lambda_handler(event, None)

    expected_calls = []
    call_params_in_order = [
        ("env1", "glue_jobs", ["glue_job1", "glue_job3"]),
        ("env2", "glue_jobs", ["glue_job2"]),
        ("env1", "glue_workflows", ["glue_workflow1"]),
    ]
    for call_param in call_params_in_order:
        expected_calls.append(
            call(
                monitored_environment_name=call_param[0],
                resource_type=call_param[1],
                resource_names=call_param[2],
                settings=ANY,
                iam_role_name=os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"],
                timestream_metrics_db_name=os.environ["TIMESTREAM_METRICS_DB_NAME"],
                last_update_times=LAST_UPDATE_TIMES_SAMPLE,
                alerts_event_bus_name=os.environ["ALERTS_EVENT_BUS_NAME"],
            )
        )

    mock_process_all_resources_by_env_and_type.assert_has_calls(expected_calls)

#########################################################################################