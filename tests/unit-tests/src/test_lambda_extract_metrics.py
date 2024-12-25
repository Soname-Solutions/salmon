from datetime import datetime, timezone
import pytest
import os

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lambda_extract_metrics import (
    lambda_handler,
    process_all_resources_by_env_and_type,
    process_individual_resource,
    collect_glue_data_quality_result_ids,
    get_since_time_for_individual_resource,
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
            "last_update_time": "2024-04-15 12:05:11.275000000",
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
TEST_DQ_RESULT_IDS = ["result-id-1", "result-id-2"]
EARLIEST_WRITEABLE_TIME = datetime(2024, 4, 16, 0, 0, 0, 000, tzinfo=timezone.utc)
MOCKED_LAST_UPDATE_TIME = datetime(2024, 4, 16, 15, 5, 11, 200, tzinfo=timezone.utc)
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
def mock_metrics_extractor_from_provider(request):
    include_set_result_ids = (
        request.param.get("include_set_result_ids", False)
        if hasattr(request, "param")
        else False
    )

    with patch(
        "lambda_extract_metrics.MetricsExtractorProvider.get_metrics_extractor"
    ) as mock_get_extractor:
        methods = ["get_last_update_time", "prepare_metrics_data", "write_metrics"]
        if include_set_result_ids:
            methods.append("set_result_ids")

        mocked_extractor = MagicMock(spec=methods)

        mocked_extractor.get_last_update_time.return_value = MOCKED_LAST_UPDATE_TIME
        mocked_extractor.prepare_metrics_data.return_value = (
            ["record1", "record2"],
            ["common_attr1", "common_attr2"],
        )

        if "set_result_ids" in methods:
            mocked_extractor.set_result_ids.return_value = TEST_DQ_RESULT_IDS

        mock_get_extractor.return_value = mocked_extractor

        yield mocked_extractor


# @pytest.fixture(scope="function")
# def mock_timestream_writer():
#     mocked_timestream_writer = MagicMock()
#     mocked_timestream_writer.get_earliest_writeable_time_for_table.return_value = (
#         EARLIEST_WRITEABLE_TIME
#     )

#     with patch(
#         "lambda_extract_metrics.TimestreamTableWriter", mocked_timestream_writer
#     ) as mock_get_extractor:
#         yield mocked_timestream_writer


@pytest.fixture(scope="function")
def mock_metrics_storage_earliest_writeable_time():
    mocked_metrics_storage = MagicMock()
    mocked_metrics_storage.get_earliest_writeable_time_for_table.return_value = (
        EARLIEST_WRITEABLE_TIME
    )

    with patch(
        "lambda_extract_metrics.TimestreamMetricsStorage", mocked_metrics_storage
    ) as mock_get_extractor:
        yield mocked_metrics_storage


@pytest.fixture(scope="function")
def mock_boto3_client_creator():
    mocked_boto3_client_creator = MagicMock()
    mocked_boto3_client_creator.account_id.return_value = "1234567890"
    mocked_boto3_client_creator.region_id.return_value = "us-east-1"

    with patch(
        "lambda_extract_metrics.Boto3ClientCreator", mocked_boto3_client_creator
    ) as mock_get_extractor:
        yield mocked_boto3_client_creator


#########################################################################################
# TESTs for get_since_time_for_individual_resource
@pytest.mark.usefixtures("mock_metrics_storage")
class TestGetSinceTimeForIndividualResource:
    @pytest.fixture(autouse=True)
    def mock_metrics_storage(self):
        self.mocked_metrics_storage = MagicMock()
        self.mocked_metrics_storage.get_earliest_writeable_time_for_resource_type.return_value = (
            EARLIEST_WRITEABLE_TIME
        )

        with patch(
            "lambda_extract_metrics.TimestreamMetricsStorage",
            self.mocked_metrics_storage,
        ) as mock_get_extractor:
            yield mock_get_extractor

    # we have last_update_time in JSON, it's later than table's earliest_writeable_time
    # expected result - last_update_time from JSON
    def test_last_update_time_from_json(self):
        last_update_times = {"key": "doesn't matter - extract logic not tested here"}
        resource_type = "glue_jobs"
        resource_name = "glue-job1"

        # trying to write metrics later than earliest writable time (normal situation)
        since_time = datetime(2024, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.return_value = (
            since_time
        )

        result = get_since_time_for_individual_resource(
            last_update_times,
            resource_type,
            resource_name,
            self.mocked_metrics_storage,
        )

        assert result == since_time
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.assert_called_once()
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.assert_not_called()
        self.mocked_metrics_storage.get_earliest_writeable_time_for_resource_type.assert_called_once()

    # we have last_update_time in JSON, but it's earlier than table's earliest_writeable_time
    # expected result - EARLIEST_WRITEABLE_TIME
    def test_last_update_time_fallback_to_earliest(self):
        last_update_times = {"key": "doesn't matter - extract logic not tested here"}
        resource_type = "glue_jobs"
        resource_name = "glue-job1"

        # trying to write metrics EARLIER than earliest writable time (expect earliest)
        since_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.return_value = (
            since_time
        )

        result = get_since_time_for_individual_resource(
            last_update_times,
            resource_type,
            resource_name,
            self.mocked_metrics_storage,
        )

        assert result == EARLIEST_WRITEABLE_TIME
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.assert_called_once()
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.assert_not_called()
        self.mocked_metrics_storage.get_earliest_writeable_time_for_resource_type.assert_called_once()

    # we DON'T have last_update_time in JSON, but we can get it from metrics_table
    # expected result - since_time taken from storage table
    def test_last_update_time_from_metrics_table(self):
        last_update_times = {"key": "doesn't matter - extract logic not tested here"}
        resource_type = "glue_jobs"
        resource_name = "glue-job1"

        # Simulate JSON doesn't have since_time for resource. Taking from metrics table
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.return_value = (
            None
        )
        since_time = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.return_value = (
            since_time
        )

        result = get_since_time_for_individual_resource(
            last_update_times,
            resource_type,
            resource_name,
            self.mocked_metrics_storage,
        )

        assert result == since_time
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.assert_called_once()
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.assert_called_once_with(
            resource_type=resource_type, resource_name=resource_name
        )
        self.mocked_metrics_storage.get_earliest_writeable_time_for_resource_type.assert_called_once()

    # No last_update_time in JSON or metrics table, fallback to earliest writeable time
    def test_no_last_update_time_fallback_to_earliest(self):
        last_update_times = {"key": "doesn't matter - extract logic not tested here"}
        resource_type = "glue_jobs"
        resource_name = "glue-job1"

        # No last_update_time in JSON or metrics table, fallback to earliest writeable time
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.return_value = (
            None
        )
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.return_value = (
            None
        )

        result = get_since_time_for_individual_resource(
            last_update_times,
            resource_type,
            resource_name,
            self.mocked_metrics_storage,
        )

        assert result == EARLIEST_WRITEABLE_TIME
        self.mocked_metrics_storage.get_resource_last_update_time_from_json.assert_called_once()
        self.mocked_metrics_storage.get_last_update_time_from_metrics_table.assert_called_once_with(
            resource_type=resource_type, resource_name=resource_name
        )
        self.mocked_metrics_storage.get_earliest_writeable_time_for_resource_type.assert_called_once()


#########################################################################################
# # TESTs for process_individual_resource


@pytest.mark.usefixtures("mock_dependencies")
class TestProcessIndividualResource:
    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        # Mock dependencies
        self.mock_boto3_client_creator = MagicMock()
        self.mock_metrics_storage = MagicMock()
        self.mock_metrics_extractor = MagicMock()
        self.mock_metrics_extractor.mock_add_spec(
            ["prepare_metrics_data", "write_metrics", "set_result_ids"]
        )
        self.mock_metrics_extractor_provider = patch(
            "lambda_extract_metrics.MetricsExtractorProvider.get_metrics_extractor",
            return_value=self.mock_metrics_extractor,
        )
        self.mock_get_since_time = patch(
            "lambda_extract_metrics.get_since_time_for_individual_resource",
            return_value=EARLIEST_WRITEABLE_TIME,
        )

        self.mock_metrics_extractor_provider.start()
        self.mock_get_since_time.start()

        yield

        self.mock_metrics_extractor_provider.stop()
        self.mock_get_since_time.stop()

    def test_process_metrics_successfully(self):
        # Arrange
        resource_type = "glue_jobs"
        resource_name = "glue-job1"
        monitored_environment_name = "test_env"
        metrics_table_name = "test_metrics_table"
        alerts_event_bus_name = "test_event_bus"
        last_update_times = {}
        result_ids = []

        records = ["record1", "record2"]
        common_attributes = ["attr1", "attr2"]

        self.mock_metrics_extractor.prepare_metrics_data.return_value = (
            records,
            common_attributes,
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.return_value = (
            metrics_table_name
        )

        # Act
        result = process_individual_resource(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_name=resource_name,
            boto3_client_creator=self.mock_boto3_client_creator,
            aws_client_name="glue",
            metrics_storage=self.mock_metrics_storage,
            metrics_table_name=metrics_table_name,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
            result_ids=result_ids,
        )

        # Assert
        assert result["metrics_records_written"] == len(records)
        assert result["alerts_sent"] is False, "Alerts shouldn't be sent in this call"
        assert result["since_time"] == EARLIEST_WRITEABLE_TIME

        self.mock_metrics_extractor.prepare_metrics_data.assert_called_once_with(
            since_time=EARLIEST_WRITEABLE_TIME
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.assert_called_once_with(
            resource_type=resource_type
        )
        self.mock_metrics_extractor.write_metrics.assert_called_once_with(
            metrics_table_name=metrics_table_name,
            metrics_storage=self.mock_metrics_storage,
            records=records,
            common_attributes=common_attributes,
        )

    def test_process_with_alerts_sent(self):
        # Arrange
        resource_type = "glue_workflows"
        resource_name = "workflow1"
        monitored_environment_name = "test_env"
        metrics_table_name = "test_metrics_table"
        alerts_event_bus_name = "test_event_bus"
        last_update_times = {}
        result_ids = []

        records = ["record1"]
        common_attributes = ["attr1"]

        self.mock_metrics_extractor.prepare_metrics_data.return_value = (
            records,
            common_attributes,
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.return_value = (
            metrics_table_name
        )
        self.mock_metrics_extractor.send_alerts = MagicMock()  # enabling this method

        # Act
        result = process_individual_resource(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_name=resource_name,
            boto3_client_creator=self.mock_boto3_client_creator,
            aws_client_name="stepfunctions",
            metrics_storage=self.mock_metrics_storage,
            metrics_table_name=metrics_table_name,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
            result_ids=result_ids,
        )

        # Assert
        assert result["metrics_records_written"] == len(records)
        assert result["alerts_sent"] is True, "Alerts should be sent in this call"

        self.mock_metrics_extractor.send_alerts.assert_called_once_with(
            alerts_event_bus_name,
            self.mock_boto3_client_creator.account_id,
            self.mock_boto3_client_creator.region,
        )

    def test_process_glue_data_quality_with_result_ids(self):
        # Arrange
        resource_type = types.GLUE_DATA_QUALITY
        resource_name = "dq-rule"
        monitored_environment_name = "test_env"
        metrics_table_name = "test_metrics_table"
        alerts_event_bus_name = "test_event_bus"
        last_update_times = {}
        result_ids = ["result1", "result2"]

        records = []
        common_attributes = []

        self.mock_metrics_extractor.prepare_metrics_data.return_value = (
            records,
            common_attributes,
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.return_value = (
            metrics_table_name
        )

        # Act
        result = process_individual_resource(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_name=resource_name,
            boto3_client_creator=self.mock_boto3_client_creator,
            aws_client_name="glue",
            metrics_storage=self.mock_metrics_storage,
            metrics_table_name=metrics_table_name,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
            result_ids=result_ids,
        )

        # Assert
        assert result["metrics_records_written"] == len(records)
        assert result["alerts_sent"] is False, "Alerts shouldn't be sent in this call"

        self.mock_metrics_extractor.set_result_ids.assert_called_once_with(
            result_ids=result_ids
        )


# #########################################################################################


@pytest.mark.usefixtures("mock_dependencies")
class TestProcessAllResourcesByEnvAndType:
    GLUE_DQ_RESULT_IDS = ["result1", "result2"]

    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        # Mock dependencies
        self.mock_settings = MagicMock()
        self.mock_metrics_storage = MagicMock()
        self.mock_boto3_client_creator = MagicMock()
        self.mock_collect_glue_data_quality_result_ids = patch(
            "lambda_extract_metrics.collect_glue_data_quality_result_ids",
            return_value=self.GLUE_DQ_RESULT_IDS,
        )
        self.mock_process_individual_resource = patch(
            "lambda_extract_metrics.process_individual_resource"
        )
        self.mock_boto3_client_creator_patch = patch(
            "lambda_extract_metrics.Boto3ClientCreator",
            return_value=self.mock_boto3_client_creator,
        )

        # Start patches
        self.mock_collect_glue_data_quality_result_ids.start()
        self.mock_process_individual_resource_mock = (
            self.mock_process_individual_resource.start()
        )
        self.mock_boto3_client_creator_patch.start()

        yield

        # Stop patches
        self.mock_collect_glue_data_quality_result_ids.stop()
        self.mock_process_individual_resource.stop()
        self.mock_boto3_client_creator_patch.stop()

    def test_process_resources_with_glue_data_quality(self):
        # Arrange
        monitored_environment_name = "test_env"
        resource_type = types.GLUE_DATA_QUALITY
        resource_names = ["resource1", "resource2"]
        last_update_times = LAST_UPDATE_TIMES_SAMPLE
        alerts_event_bus_name = "test_event_bus"

        self.mock_settings.get_monitored_environment_props.return_value = (
            "account-id",
            "region",
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.return_value = (
            "metrics_table"
        )

        # Act
        process_all_resources_by_env_and_type(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_names=resource_names,
            settings=self.mock_settings,
            iam_role_name="test-role",
            metrics_storage=self.mock_metrics_storage,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
        )

        # Assert
        self.mock_settings.get_monitored_environment_props.assert_called_once_with(
            monitored_environment_name
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.assert_called_once_with(
            resource_type
        )
        self.mock_process_individual_resource_mock.assert_has_calls(
            [
                call(
                    monitored_environment_name=monitored_environment_name,
                    resource_type=resource_type,
                    resource_name="resource1",
                    boto3_client_creator=self.mock_boto3_client_creator,
                    aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                        resource_type
                    ],
                    metrics_storage=self.mock_metrics_storage,
                    metrics_table_name="metrics_table",
                    last_update_times=last_update_times,
                    alerts_event_bus_name=alerts_event_bus_name,
                    result_ids=self.GLUE_DQ_RESULT_IDS,
                ),
                call(
                    monitored_environment_name=monitored_environment_name,
                    resource_type=resource_type,
                    resource_name="resource2",
                    boto3_client_creator=self.mock_boto3_client_creator,
                    aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                        resource_type
                    ],
                    metrics_storage=self.mock_metrics_storage,
                    metrics_table_name="metrics_table",
                    last_update_times=last_update_times,
                    alerts_event_bus_name=alerts_event_bus_name,
                    result_ids=self.GLUE_DQ_RESULT_IDS,
                ),
            ]
        )

    def test_process_resources_without_glue_data_quality(self):
        # Arrange
        monitored_environment_name = "test_env"
        resource_type = "glue_jobs"
        resource_names = ["job1", "job2"]
        last_update_times = {}
        alerts_event_bus_name = "test_event_bus"

        self.mock_settings.get_monitored_environment_props.return_value = (
            "account-id",
            "region",
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.return_value = (
            "metrics_table"
        )

        # Act
        process_all_resources_by_env_and_type(
            monitored_environment_name=monitored_environment_name,
            resource_type=resource_type,
            resource_names=resource_names,
            settings=self.mock_settings,
            iam_role_name="test-role",
            metrics_storage=self.mock_metrics_storage,
            last_update_times=last_update_times,
            alerts_event_bus_name=alerts_event_bus_name,
        )

        # Assert
        self.mock_settings.get_monitored_environment_props.assert_called_once_with(
            monitored_environment_name
        )
        self.mock_metrics_storage.get_metrics_table_name_for_resource_type.assert_called_once_with(
            resource_type
        )
        self.mock_process_individual_resource_mock.assert_has_calls(
            [
                call(
                    monitored_environment_name=monitored_environment_name,
                    resource_type=resource_type,
                    resource_name="job1",
                    boto3_client_creator=self.mock_boto3_client_creator,
                    aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                        resource_type
                    ],
                    metrics_storage=self.mock_metrics_storage,
                    metrics_table_name="metrics_table",
                    last_update_times=last_update_times,
                    alerts_event_bus_name=alerts_event_bus_name,
                    result_ids=[],
                ),
                call(
                    monitored_environment_name=monitored_environment_name,
                    resource_type=resource_type,
                    resource_name="job2",
                    boto3_client_creator=self.mock_boto3_client_creator,
                    aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                        resource_type
                    ],
                    metrics_storage=self.mock_metrics_storage,
                    metrics_table_name="metrics_table",
                    last_update_times=last_update_times,
                    alerts_event_bus_name=alerts_event_bus_name,
                    result_ids=[],
                ),
            ]
        )


# #########################################################################################
# def test_lambda_handler_empty_group_content(
#     os_vars_init, mock_settings, mock_process_all_resources_by_env_and_type
# ):
#     monitoring_group = "group1"
#     event = {
#         "monitoring_group": monitoring_group,
#         "last_update_times": LAST_UPDATE_TIMES_SAMPLE,
#     }

#     # checking no calls to process_all_resources_by_env_and_type made and no lambda failure
#     group_context = {}

#     with patch(
#         "test_lambda_extract_metrics.MockedSettings.get_monitoring_group_content",
#         return_value=group_context,
#     ):
#         lambda_handler(event, None)

#     mock_process_all_resources_by_env_and_type.assert_not_called()


# def test_lambda_handler_with_group_content(
#     os_vars_init,
#     mock_settings,
#     mock_process_all_resources_by_env_and_type,
#     os_vars_values,
# ):
#     monitoring_group = "group1"
#     event = {
#         "monitoring_group": monitoring_group,
#         "last_update_times": LAST_UPDATE_TIMES_SAMPLE,
#     }

#     # checking calls to process_all_resources_by_env_and_type are made in a specific order
#     # and resources are grouped properly (by env and resource type)
#     group_context = {
#         "group_name": "salmonts_workflows_sparkjobs",
#         "glue_jobs": [
#             {"name": "glue_job1", "monitored_environment_name": "env1"},
#             {"name": "glue_job2", "monitored_environment_name": "env2"},
#             {"name": "glue_job3", "monitored_environment_name": "env1"},
#         ],
#         "glue_workflows": [
#             {"name": "glue_workflow1", "monitored_environment_name": "env1"}
#         ],
#     }

#     with patch(
#         "test_lambda_extract_metrics.MockedSettings.get_monitoring_group_content",
#         return_value=group_context,
#     ):
#         lambda_handler(event, None)

#     expected_calls = []
#     call_params_in_order = [
#         ("env1", "glue_jobs", ["glue_job1", "glue_job3"]),
#         ("env2", "glue_jobs", ["glue_job2"]),
#         ("env1", "glue_workflows", ["glue_workflow1"]),
#     ]
#     (
#         settings_s3_path,
#         iam_role_name,
#         timestream_metrics_db_name,
#         alerts_event_bus_name,
#     ) = os_vars_values
#     for call_param in call_params_in_order:
#         expected_calls.append(
#             call(
#                 monitored_environment_name=call_param[0],
#                 resource_type=call_param[1],
#                 resource_names=call_param[2],
#                 settings=ANY,
#                 iam_role_name=iam_role_name,
#                 timestream_metrics_db_name=timestream_metrics_db_name,
#                 last_update_times=LAST_UPDATE_TIMES_SAMPLE,
#                 alerts_event_bus_name=alerts_event_bus_name,
#             )
#         )

#     mock_process_all_resources_by_env_and_type.assert_has_calls(expected_calls)


# #########################################################################################


@pytest.mark.usefixtures("mock_dependencies")
class TestCollectGlueDataQualityResultIds:
    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        # Mock dependencies
        self.mock_boto3_client_creator = MagicMock()
        self.mock_metrics_storage = MagicMock()
        self.mock_glue_manager = MagicMock()

        # Patch `GlueManager` and `get_client`
        self.mock_glue_manager_patch = patch(
            "lambda_extract_metrics.GlueManager", return_value=self.mock_glue_manager
        )
        self.mock_get_client_patch = patch.object(
            self.mock_boto3_client_creator, "get_client"
        )

        # Start patches
        self.mock_glue_manager_patch.start()
        self.mock_get_client_patch.start()

        yield

        # Stop patches
        self.mock_glue_manager_patch.stop()
        self.mock_get_client_patch.stop()

    def test_collect_result_ids_success(self):
        # Arrange
        monitored_environment_name = "test_env"
        resource_names = ["test-dq-ruleset-1", "test-de-ruleset-2"]
        dq_last_update_times = [
            {
                "resource_name": "test-dq-ruleset-1",
                "last_update_time": "2024-07-21 00:01:52.820000000",
            },
            {
                "resource_name": "test-de-ruleset-2",
                "last_update_time": "2024-07-22 00:01:56.042000000",
            },
        ]
        min_last_update_time = str_utc_datetime_to_datetime(
            "2024-07-21 00:01:52.820000000"
        )
        aws_client_name = "glue"
        metrics_table_name = "metrics_table"

        expected_result_ids = ["result1", "result2"]

        self.mock_metrics_storage.get_earliest_last_update_time_for_resource_set.return_value = (
            min_last_update_time
        )
        self.mock_glue_manager.list_data_quality_results.return_value = (
            expected_result_ids
        )

        # Act
        result = collect_glue_data_quality_result_ids(
            monitored_environment_name=monitored_environment_name,
            resource_names=resource_names,
            dq_last_update_times=dq_last_update_times,
            boto3_client_creator=self.mock_boto3_client_creator,
            aws_client_name=aws_client_name,
            metrics_storage=self.mock_metrics_storage,
            metrics_table_name=metrics_table_name,
        )

        # Assert
        assert result == expected_result_ids
        self.mock_metrics_storage.get_earliest_last_update_time_for_resource_set.assert_called_once_with(
            last_update_times=dq_last_update_times,
            resource_names=resource_names,
            metrics_table_name=metrics_table_name,
        )
        self.mock_boto3_client_creator.get_client.assert_called_once_with(
            aws_client_name=aws_client_name
        )
        self.mock_glue_manager.list_data_quality_results.assert_called_once_with(
            started_after=min_last_update_time
        )
