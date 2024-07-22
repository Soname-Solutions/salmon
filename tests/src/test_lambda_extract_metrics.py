from datetime import datetime
import pytest
import os

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lambda_extract_metrics import (
    lambda_handler,
    process_all_resources_by_env_and_type,
    process_individual_resource,
    collect_glue_data_quality_result_ids,
)
from unittest.mock import patch, call, MagicMock, ANY
from lib.core.constants import SettingConfigs, SettingConfigResourceTypes as types

# uncomment this to see lambda's logging output
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

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
    "glue_workflows": [
        {
            "resource_name": "glue-workflow1",
            "last_update_time": "2024-04-16 12:05:11.275000000",
        },
    ],
}
#########################################################################################


@pytest.fixture(scope="module", autouse=True)
def os_vars_init(aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    stage_name = "teststage"
    os.environ[
        "IAMROLE_MONITORED_ACC_EXTRACT_METRICS"
    ] = f"role-salmon-monitored-acc-extract-metrics-{stage_name}"
    os.environ[
        "TIMESTREAM_METRICS_DB_NAME"
    ] = f"timestream-salmon-metrics-events-storage-{stage_name}"
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ["ALERTS_EVENT_BUS_NAME"] = f"eventbus-salmon-alerting-{stage_name}"


@pytest.fixture(scope="module")
def os_vars_values(os_vars_init):
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    iam_role_name = os.environ["IAMROLE_MONITORED_ACC_EXTRACT_METRICS"]
    timestream_metrics_db_name = os.environ["TIMESTREAM_METRICS_DB_NAME"]
    alerts_event_bus_name = os.environ["ALERTS_EVENT_BUS_NAME"]

    return (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    )


#########################################################################################


class MockedSettings:
    @classmethod
    def from_s3_path(cls, base_path: str, iam_role_list_monitored_res: str = None):
        return MockedSettings()

    def get_monitoring_group_content(self, group_name: str) -> dict:
        return {"content": "define in a specific test"}

    def get_monitored_environment_props(self):
        return "1234567890", "us-east-1"


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


@pytest.fixture(scope="function")
def mock_process_individual_resource():
    with patch("lambda_extract_metrics.process_individual_resource") as mocked_function:
        yield mocked_function


@pytest.fixture(scope="function")
def mock_metrics_extractor_from_provider():
    with patch(
        "lambda_extract_metrics.MetricsExtractorProvider.get_metrics_extractor"
    ) as mock_get_extractor:
        mocked_extractor = MagicMock(
            spec=["get_last_update_time", "prepare_metrics_data", "write_metrics"]
        )

        mocked_extractor.get_last_update_time.return_value = (
            "2024-04-16 12:05:11.275000000"
        )

        mocked_extractor.prepare_metrics_data.return_value = (
            ["record1", "record2"],
            ["common_attr1", "common_attr2"],
        )

        mock_get_extractor.return_value = mocked_extractor

        yield mocked_extractor


@pytest.fixture(scope="function")
def mock_timestream_writer():
    mocked_timestream_writer = MagicMock()
    mocked_timestream_writer.get_earliest_writeable_time_for_table.return_value = (
        datetime(2000, 1, 1, 0, 0, 0)
    )

    with patch(
        "lambda_extract_metrics.TimestreamTableWriter", mocked_timestream_writer
    ) as mock_get_extractor:
        yield mocked_timestream_writer


@pytest.fixture(scope="function")
def mock_boto3_client_creator():
    mocked_boto3_client_creator = MagicMock()
    mocked_boto3_client_creator.account_id.return_value = "1234567890"
    mocked_boto3_client_creator.region_id.return_value = "us-east-1"

    with patch(
        "lambda_extract_metrics.Boto3ClientCreator", mocked_boto3_client_creator
    ) as mock_get_extractor:
        yield mocked_boto3_client_creator


@pytest.fixture(scope="function", autouse=True)
def mock_glue_client():
    mock_glue_client = MagicMock()
    results = {"Results": [{"ResultId": "result1"}, {"ResultId": "result2"}]}
    mock_glue_client.list_data_quality_results.return_value = results
    mock_glue_client.batch_get_data_quality_result.return_value = {}
    with patch("boto3.client", return_value=mock_glue_client) as mock_glue:
        yield mock_glue


#########################################################################################


# testing successful flow when we have last_update_time for the resource coming from orchestrator lambda
def test_process_individual_resource_with_last_upd_time(
    os_vars_values,
    mock_settings,
    mock_metrics_extractor_from_provider,
    mock_timestream_writer,
    mock_boto3_client_creator,
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values
    monitored_environment_name = "env1"
    resource_type = "glue_jobs"
    resource_name = (
        "glue-job1"  # we have upd time for this glue job in LAST_UPDATE_TIMES_SAMPLE
    )

    boto3_client_creator = mock_boto3_client_creator
    timestream_writer = mock_timestream_writer
    timestream_metrics_table_name = "test_table_name"

    result = process_individual_resource(
        monitored_environment_name=monitored_environment_name,
        resource_type=resource_type,
        resource_name=resource_name,
        boto3_client_creator=boto3_client_creator,
        aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
            resource_type
        ],
        timestream_writer=timestream_writer,
        timestream_metrics_db_name=timestream_metrics_db_name,
        timestream_metrics_table_name=timestream_metrics_table_name,
        last_update_times=LAST_UPDATE_TIMES_SAMPLE,
        alerts_event_bus_name=alerts_event_bus_name,
        result_ids=[],
    )

    # Assert last_update_time is taken directly from arguments
    # not from: metrics_extractor.get_last_update_time
    # not from: timestream_writer.get_earliest_writeable_time_for_table
    mock_metrics_extractor_from_provider.get_last_update_time.assert_not_called()
    mock_timestream_writer.get_earliest_writeable_time_for_table.assert_not_called()

    # no alerts sent (glue uses eventbridge for alerts)
    assert result["alerts_sent"] == False, "Alerts shouldn't be sent in this call"


# testing successful flow when we DON'T have last_update_time for the resource coming from orchestrator lambda
# but we can identify it from timestream DB
def test_process_individual_resource_last_upd_time_from_timestream(
    os_vars_values,
    mock_settings,
    mock_metrics_extractor_from_provider,
    mock_timestream_writer,
    mock_boto3_client_creator,
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values
    monitored_environment_name = "env1"
    resource_type = "glue_jobs"
    resource_name = "glue-job-not-having-last-upd-time"  # we DON'T have upd time for this glue job in LAST_UPDATE_TIMES_SAMPLE

    boto3_client_creator = mock_boto3_client_creator
    timestream_writer = mock_timestream_writer
    timestream_metrics_table_name = "test_table_name"

    result = process_individual_resource(
        monitored_environment_name=monitored_environment_name,
        resource_type=resource_type,
        resource_name=resource_name,
        boto3_client_creator=boto3_client_creator,
        aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
            resource_type
        ],
        timestream_writer=timestream_writer,
        timestream_metrics_db_name=timestream_metrics_db_name,
        timestream_metrics_table_name=timestream_metrics_table_name,
        last_update_times=LAST_UPDATE_TIMES_SAMPLE,
        alerts_event_bus_name=alerts_event_bus_name,
        result_ids=[],
    )

    # Assert last_update_time is taken directly from arguments
    # not from: metrics_extractor.get_last_update_time
    # not from: timestream_writer.get_earliest_writeable_time_for_table
    mock_metrics_extractor_from_provider.get_last_update_time.assert_called_once()
    mock_timestream_writer.get_earliest_writeable_time_for_table.assert_not_called()

    # no alerts sent (glue uses eventbridge for alerts)
    assert result["alerts_sent"] == False, "Alerts shouldn't be sent in this call"


# testing successful flow when we DON'T have last_update_time neither from orch lambda,
# nor from timestream DB
# getting from last writeable time from TS table settings
def test_process_individual_resource_no_last_upd_time(
    os_vars_values,
    mock_settings,
    mock_metrics_extractor_from_provider,
    mock_timestream_writer,
    mock_boto3_client_creator,
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values
    monitored_environment_name = "env1"
    resource_type = "glue_jobs"
    resource_name = "glue-job-not-having-last-upd-time"  # we DON'T have upd time for this glue job in LAST_UPDATE_TIMES_SAMPLE

    boto3_client_creator = mock_boto3_client_creator
    timestream_writer = mock_timestream_writer
    timestream_metrics_table_name = "test_table_name"

    with patch.object(
        mock_metrics_extractor_from_provider, "get_last_update_time", return_value=None
    ):
        result = process_individual_resource(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_name=resource_name,
            boto3_client_creator=boto3_client_creator,
            aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                resource_type
            ],
            timestream_writer=timestream_writer,
            timestream_metrics_db_name=timestream_metrics_db_name,
            timestream_metrics_table_name=timestream_metrics_table_name,
            last_update_times=LAST_UPDATE_TIMES_SAMPLE,
            alerts_event_bus_name=alerts_event_bus_name,
            result_ids=[],
        )

        # Assert last_update_time is taken directly from arguments
        # not from: metrics_extractor.get_last_update_time
        # not from: timestream_writer.get_earliest_writeable_time_for_table
        mock_metrics_extractor_from_provider.get_last_update_time.assert_called_once()
        mock_timestream_writer.get_earliest_writeable_time_for_table.assert_called_once()

        # no alerts sent (glue uses eventbridge for alerts)
        assert result["alerts_sent"] == False, "Alerts shouldn't be sent in this call"


# testing flow when specific resource type requires sending alerts
def test_process_individual_resource_send_alerts(
    os_vars_values,
    mock_settings,
    mock_metrics_extractor_from_provider,
    mock_timestream_writer,
    mock_boto3_client_creator,
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values
    monitored_environment_name = "env1"
    resource_type = (
        "glue_workflows"  # workflow type requires sending alerts from extract lambda
    )
    resource_name = "glue-workflow1"

    boto3_client_creator = mock_boto3_client_creator
    timestream_writer = mock_timestream_writer
    timestream_metrics_table_name = "test_table_name"

    mock_metrics_extractor_from_provider.mock_add_spec(
        spec=[
            "get_last_update_time",
            "prepare_metrics_data",
            "write_metrics",
            "send_alerts",
        ]
    )

    result = process_individual_resource(
        monitored_environment_name=monitored_environment_name,
        resource_type=resource_type,
        resource_name=resource_name,
        boto3_client_creator=boto3_client_creator,
        aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
            resource_type
        ],
        timestream_writer=timestream_writer,
        timestream_metrics_db_name=timestream_metrics_db_name,
        timestream_metrics_table_name=timestream_metrics_table_name,
        last_update_times=LAST_UPDATE_TIMES_SAMPLE,
        alerts_event_bus_name=alerts_event_bus_name,
        result_ids=[],
    )

    # no alerts sent (glue uses eventbridge for alerts)
    assert result["alerts_sent"] == True, "Alerts should be sent in this call"


#########################################################################################


def test_process_all_resources_by_env_and_type_glue_jobs(
    os_vars_values, mock_settings, mock_process_individual_resource
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values

    # making sure calls for process_individual_resource are made and proper AWS client is used
    monitored_environment_name = "env1"
    resource_type = "glue_jobs"
    resource_names = ["glue_job1", "glue_job2"]

    process_all_resources_by_env_and_type(
        monitored_environment_name=monitored_environment_name,
        resource_type=resource_type,
        resource_names=resource_names,
        settings=mock_settings,
        iam_role_name=iam_role_name,
        timestream_metrics_db_name=timestream_metrics_db_name,
        last_update_times=LAST_UPDATE_TIMES_SAMPLE,
        alerts_event_bus_name=alerts_event_bus_name,
    )

    # mock process_individual_resource
    expected_calls = []
    for resource_name in resource_names:
        expected_calls.append(
            call(
                monitored_environment_name=monitored_environment_name,
                resource_type=resource_type,
                resource_name=resource_name,
                boto3_client_creator=ANY,
                aws_client_name="glue",
                timestream_writer=ANY,
                timestream_metrics_db_name=timestream_metrics_db_name,
                timestream_metrics_table_name=ANY,
                last_update_times=LAST_UPDATE_TIMES_SAMPLE,
                alerts_event_bus_name=alerts_event_bus_name,
                result_ids=[],
            )
        )

    mock_process_individual_resource.assert_has_calls(expected_calls)


def test_process_all_resources_by_env_and_type_glue_workflows(
    os_vars_values, mock_settings, mock_process_individual_resource
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values

    # making sure calls for process_individual_resource are made and proper AWS client is used
    monitored_environment_name = "env1"
    resource_type = "glue_workflows"
    resource_names = ["glue_workflow1"]

    process_all_resources_by_env_and_type(
        monitored_environment_name=monitored_environment_name,
        resource_type=resource_type,
        resource_names=resource_names,
        settings=mock_settings,
        iam_role_name=iam_role_name,
        timestream_metrics_db_name=timestream_metrics_db_name,
        last_update_times=LAST_UPDATE_TIMES_SAMPLE,
        alerts_event_bus_name=alerts_event_bus_name,
    )

    # mock process_individual_resource
    expected_calls = []
    for resource_name in resource_names:
        expected_calls.append(
            call(
                monitored_environment_name=monitored_environment_name,
                resource_type=resource_type,
                resource_name=resource_name,
                boto3_client_creator=ANY,
                aws_client_name="glue",
                timestream_writer=ANY,
                timestream_metrics_db_name=timestream_metrics_db_name,
                timestream_metrics_table_name=ANY,
                last_update_times=LAST_UPDATE_TIMES_SAMPLE,
                alerts_event_bus_name=alerts_event_bus_name,
                result_ids=[],
            )
        )

    mock_process_individual_resource.assert_has_calls(expected_calls)


def test_process_all_resources_by_env_and_type_glue_data_quality(
    os_vars_values,
    mock_settings,
    mock_process_individual_resource,
):
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values

    # making sure calls for process_individual_resource are made and proper AWS client is used
    monitored_environment_name = "env1"
    resource_type = types.GLUE_DATA_QUALITY
    resource_names = ["glue_dq1", "glue_dq2"]

    with patch(
        "lambda_extract_metrics.collect_glue_data_quality_result_ids",
        return_value=["test_result_id1", "test_result_id2"],
    ):
        process_all_resources_by_env_and_type(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_names=resource_names,
            settings=mock_settings,
            iam_role_name=iam_role_name,
            timestream_metrics_db_name=timestream_metrics_db_name,
            last_update_times=LAST_UPDATE_TIMES_SAMPLE,
            alerts_event_bus_name=alerts_event_bus_name,
        )

    # mock process_individual_resource
    expected_calls = []
    for resource_name in resource_names:
        expected_calls.append(
            call(
                monitored_environment_name=monitored_environment_name,
                resource_type=resource_type,
                resource_name=resource_name,
                boto3_client_creator=ANY,
                aws_client_name="glue",
                timestream_writer=ANY,
                timestream_metrics_db_name=timestream_metrics_db_name,
                timestream_metrics_table_name=ANY,
                last_update_times=LAST_UPDATE_TIMES_SAMPLE,
                alerts_event_bus_name=alerts_event_bus_name,
                result_ids=["test_result_id1", "test_result_id2"],
            )
        )

    mock_process_individual_resource.assert_has_calls(expected_calls)


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
    os_vars_init,
    mock_settings,
    mock_process_all_resources_by_env_and_type,
    os_vars_values,
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
    (
        settings_s3_path,
        iam_role_name,
        timestream_metrics_db_name,
        alerts_event_bus_name,
    ) = os_vars_values
    for call_param in call_params_in_order:
        expected_calls.append(
            call(
                monitored_environment_name=call_param[0],
                resource_type=call_param[1],
                resource_names=call_param[2],
                settings=ANY,
                iam_role_name=iam_role_name,
                timestream_metrics_db_name=timestream_metrics_db_name,
                last_update_times=LAST_UPDATE_TIMES_SAMPLE,
                alerts_event_bus_name=alerts_event_bus_name,
            )
        )

    mock_process_all_resources_by_env_and_type.assert_has_calls(expected_calls)


#########################################################################################


def test_collect_glue_data_quality_result_ids(
    mock_boto3_client_creator, mock_timestream_writer
):
    monitored_environment_name = "test_env"
    resource_names = ["test-dq-ruleset-1", "test-de-ruleset-2"]
    last_update_times = [
        {
            "resource_name": "test-dq-ruleset-1",
            "last_update_time": "2024-07-21 00:01:52.820000000",
        },
        {
            "resource_name": "test-de-ruleset-2",
            "last_update_time": "2024-07-22 00:01:56.042000000",
        },
    ]
    aws_client_name = "glue"
    expected_result_ids = ["result1", "result2"]

    with patch(
        "lib.aws.GlueManager.list_data_quality_results",
        return_value=expected_result_ids,
    ) as mock_list_data_quality_results:
        returned_result_ids = collect_glue_data_quality_result_ids(
            monitored_environment_name=monitored_environment_name,
            resource_names=resource_names,
            last_update_times=last_update_times,
            boto3_client_creator=mock_boto3_client_creator,
            aws_client_name=aws_client_name,
            timestream_writer=mock_timestream_writer,
        )
    mock_boto3_client_creator.get_client.assert_called_once_with(
        aws_client_name=aws_client_name
    )
    mock_list_data_quality_results.assert_called_once_with(
        started_after=str_utc_datetime_to_datetime(
            "2024-07-21 00:01:52.820000000"
        )  # min last_update_time
    )

    assert returned_result_ids == expected_result_ids
