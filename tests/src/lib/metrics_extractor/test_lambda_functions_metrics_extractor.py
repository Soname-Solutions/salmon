from datetime import datetime

from lib.metrics_extractor import LambdaFunctionsMetricExtractor
from lib.aws.lambda_manager import LambdaManager, LambdaExecution

from common import (
    boto3_client_creator,
    get_measure_value,
    get_dimension_value,
    contains_required_items,
)
from unittest.mock import patch
import pytest

REGION = "us-east-1"
ACCOUNT_ID = "1234567890"
LAMBDA_NAME = "lambda-1"
LOG_STREAM = "test-log-stream"
LAMBDA_MANAGER_CLASS_NAME = (
    "lib.metrics_extractor.lambda_functions_metrics_extractor.LambdaManager"
)
GET_EXECUTIONS_METHOD_NAME = f"{LAMBDA_MANAGER_CLASS_NAME}.get_lambda_logs"

EVENTS_MANAGER_CLASS_NAME = (
    "lib.metrics_extractor.glue_workflows_metrics_extractor.EventsManager"
)
PUT_EVENTS_METHOD_NAME = f"{EVENTS_MANAGER_CLASS_NAME}.put_events"

EXEC_SUCCESS1 = LambdaExecution(
    LambdaName=LAMBDA_NAME,
    LogStream=LOG_STREAM,
    Status=LambdaManager.LAMBDA_SUCCESS_STATE,
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 1, 0),
    Errors=["REPORT RequestId: ff12345-kk123 Execution completed OK"],
    RequestId="ff12345-kk123",
    Report="REPORT details",
)

EXEC_SUCCESS2 = LambdaExecution(
    LambdaName=LAMBDA_NAME,
    LogStream=LOG_STREAM,
    Status=LambdaManager.LAMBDA_SUCCESS_STATE,
    StartedOn=datetime(2024, 1, 1, 1, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 1, 0),
    Errors=["REPORT RequestId: ff56789-kk123 Execution completed OK"],
    RequestId="ff56789-kk123",
    Report="REPORT details",
)

EXEC_ERROR1_WITH_REQUEST_ID = LambdaExecution(
    LambdaName=LAMBDA_NAME,
    LogStream=LOG_STREAM,
    Status=LambdaManager.LAMBDA_FAILURE_STATE,
    StartedOn=datetime(2024, 1, 1, 2, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 1, 0),
    Errors=["[ERROR] RequestId: ff56789-kk123 Something awful has happened"],
    RequestId="ff56789-kk123",
    Report="REPORT details",
)

EXEC_ERROR1_NO_REQUEST_ID = LambdaExecution(
    LambdaName=LAMBDA_NAME,
    LogStream=LOG_STREAM,
    Status=LambdaManager.LAMBDA_FAILURE_STATE,
    StartedOn=datetime(2024, 1, 1, 3, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 1, 0),
    Errors=["[ERROR] It was bad. Just bad"],
    RequestId=None,
    Report="REPORT details",
)


####################################################################


# here we check number of records returned and fields (dimensions and metric values)
def test_two_completed_records_integrity(boto3_client_creator):
    # explicitly return 2 good records
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [EXEC_SUCCESS1, EXEC_SUCCESS2]

        extractor = LambdaFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="lambda",
            resource_name=LAMBDA_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["lambda_function_request_id"]
        required_metrics = [
            "execution",
            "duration_ms",
            "max_memory_used_mb",
            "billed_duration_ms",
            "GB_seconds",
            "memory_size_mb",
            # "error_message",
        ]

        record_in_scope = records[0]

        mocked_get_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be two run records"  # we got both records

        assert contains_required_items(
            record_in_scope, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_in_scope, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


# here we check number of records returned and fields (dimensions and metric values)
def test_error_entries(boto3_client_creator):
    # explicitly return 2 good records
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [
            EXEC_ERROR1_WITH_REQUEST_ID,
            EXEC_ERROR1_NO_REQUEST_ID,
        ]

        extractor = LambdaFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="lambda",
            resource_name=LAMBDA_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["lambda_function_request_id"]
        required_metrics = [
            "error_message",
        ]

        record_with_request_id = records[0]
        record_without_request_id = records[1]

        mocked_get_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be two run records"  # we got both records

        assert contains_required_items(
            record_with_request_id, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_with_request_id, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"
        assert contains_required_items(
            record_without_request_id, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_without_request_id, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"

        assert get_dimension_value(
            record_with_request_id, "lambda_function_request_id"
        ) == str(EXEC_ERROR1_WITH_REQUEST_ID.RequestId)


# here we check handling failed jobs
def test_send_alerts(boto3_client_creator):
    # explicitly return 2 good records, (1 is not completed)
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [
            EXEC_ERROR1_WITH_REQUEST_ID,
            EXEC_ERROR1_NO_REQUEST_ID,
        ]

        extractor = LambdaFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="lambda",
            resource_name=LAMBDA_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(since_time=since_time)

        with patch(PUT_EVENTS_METHOD_NAME) as mocked_put_events:
            alerts_event_bus_name = "dummy_bus_name"
            ret_val = extractor.send_alerts(
                alerts_event_bus_name,
                boto3_client_creator.account_id,
                boto3_client_creator.region,
            )

            mocked_put_events.assert_called_once()  # sent alert to eventbus
            assert (
                ret_val["events_sent"] == 2
            )  # Both succeeded and failed events are sent. Running - skipped
