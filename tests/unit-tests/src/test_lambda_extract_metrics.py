from datetime import datetime, timezone
import pytest

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lambda_extract_metrics import (
    lambda_handler,
    process_all_resources_by_env_and_type,
    process_individual_resource,
    collect_glue_data_quality_result_ids,
    get_since_time_for_individual_resource,
)
from unittest.mock import patch, call, MagicMock
from lib.core.constants import SettingConfigs, SettingConfigResourceTypes as types

# # uncomment this to see lambda's logging output
# import logging

# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# logger.addHandler(handler)

#########################################################################################

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

EARLIEST_WRITEABLE_TIME = datetime(2024, 4, 16, 0, 0, 0, 000, tzinfo=timezone.utc)


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
            "lambda_extract_metrics.BaseMetricsStorage",
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
# TESTs for process_individual_resource


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


#########################################################################################


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


#########################################################################################


@pytest.mark.usefixtures("mock_dependencies")
class TestLambdaHandler:
    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        # Mock environment variables
        self.mock_env = patch.dict(
            "os.environ",
            {
                "SETTINGS_S3_PATH": "s3://test-bucket/settings.json",
                "IAMROLE_MONITORED_ACC_EXTRACT_METRICS": "test-iam-role",
                "METRICS_DB_NAME": "test-db",
                "ALERTS_EVENT_BUS_NAME": "test-event-bus",
            },
        )

        # Mock BaseMetricsStorage
        self.mock_metrics_storage = patch(
            "lambda_extract_metrics.MetricsStorageProvider.get_metrics_storage",
            return_value=MagicMock(),
        )
        # Mock Settings
        self.mock_settings = patch("lambda_extract_metrics.Settings")
        # Mock process_all_resources_by_env_and_type
        self.mock_process_all_resources = patch(
            "lambda_extract_metrics.process_all_resources_by_env_and_type"
        )
        # Start patches
        self.mock_env.start()
        self.mock_metrics_storage_mock = self.mock_metrics_storage.start()
        self.mock_settings_mock = self.mock_settings.start()
        self.mock_process_all_resources_mock = self.mock_process_all_resources.start()

        yield

        # Stop patches
        self.mock_env.stop()
        self.mock_metrics_storage.stop()
        self.mock_settings.stop()
        self.mock_process_all_resources.stop()

    def test_lambda_handler_success(self):
        # Arrange
        event = {
            "monitoring_group": "test_group",
            "last_update_times": {"glue_jobs": {"resource1": "2024-04-15"}},
        }
        context = MagicMock()

        # Mock Settings and its methods
        mock_settings_instance = MagicMock()
        group_context = {
            "group_name": "test_group",
            "glue_jobs": [
                {"name": "glue_job1", "monitored_environment_name": "env1"},
                {"name": "glue_job2", "monitored_environment_name": "env2"},
                {"name": "glue_job3", "monitored_environment_name": "env1"},
            ],
            "glue_workflows": [
                {"name": "glue_workflow1", "monitored_environment_name": "env1"}
            ],
        }
        mock_settings_instance.get_monitoring_group_content.return_value = group_context
        self.mock_settings_mock.from_s3_path.return_value = mock_settings_instance

        # Act
        lambda_handler(event, context)

        # Assert
        self.mock_settings_mock.from_s3_path.assert_called_once_with(
            "s3://test-bucket/settings.json",
            iam_role_list_monitored_res="test-iam-role",
        )
        mock_settings_instance.get_monitoring_group_content.assert_called_once_with(
            "test_group"
        )
        self.mock_process_all_resources_mock.assert_has_calls(
            [
                call(
                    monitored_environment_name="env1",
                    resource_type="glue_jobs",
                    resource_names=["glue_job1", "glue_job3"],
                    settings=mock_settings_instance,
                    iam_role_name="test-iam-role",
                    metrics_storage=self.mock_metrics_storage_mock.return_value,
                    last_update_times=event["last_update_times"],
                    alerts_event_bus_name="test-event-bus",
                ),
                call(
                    monitored_environment_name="env2",
                    resource_type="glue_jobs",
                    resource_names=["glue_job2"],
                    settings=mock_settings_instance,
                    iam_role_name="test-iam-role",
                    metrics_storage=self.mock_metrics_storage_mock.return_value,
                    last_update_times=event["last_update_times"],
                    alerts_event_bus_name="test-event-bus",
                ),
                call(
                    monitored_environment_name="env1",
                    resource_type="glue_workflows",
                    resource_names=["glue_workflow1"],
                    settings=mock_settings_instance,
                    iam_role_name="test-iam-role",
                    metrics_storage=self.mock_metrics_storage_mock.return_value,
                    last_update_times=event["last_update_times"],
                    alerts_event_bus_name="test-event-bus",
                ),
            ]
        )

    def test_lambda_handler_no_resources(self):
        # Arrange
        event = {
            "monitoring_group": "test_group",
            "last_update_times": {},
        }
        context = MagicMock()

        # Mock Settings and its methods
        mock_settings_instance = MagicMock()
        mock_settings_instance.get_monitoring_group_content.return_value = {}
        self.mock_settings_mock.from_s3_path.return_value = mock_settings_instance

        # Act
        lambda_handler(event, context)

        # Assert
        self.mock_settings_mock.from_s3_path.assert_called_once_with(
            "s3://test-bucket/settings.json",
            iam_role_list_monitored_res="test-iam-role",
        )
        mock_settings_instance.get_monitoring_group_content.assert_called_once_with(
            "test_group"
        )
        self.mock_process_all_resources_mock.assert_not_called()


#########################################################################################


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
            resource_type=types.GLUE_DATA_QUALITY,
        )

        # Assert
        assert result == expected_result_ids
        self.mock_metrics_storage.get_earliest_last_update_time_for_resource_set.assert_called_once_with(
            last_update_times=dq_last_update_times,
            resource_names=resource_names,
            resource_type=types.GLUE_DATA_QUALITY,
        )
        self.mock_boto3_client_creator.get_client.assert_called_once_with(
            aws_client_name=aws_client_name
        )
        self.mock_glue_manager.list_data_quality_results.assert_called_once_with(
            started_after=min_last_update_time
        )
