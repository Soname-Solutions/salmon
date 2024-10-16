from datetime import datetime

from lib.metrics_extractor import StepFunctionsMetricExtractor
from lib.aws.step_functions_manager import ExecutionData

from common import boto3_client_creator, get_measure_value, contains_required_items
from unittest.mock import patch
import pytest

REGION = "us-east-1"
ACCOUNT_ID = "1234567890"
STEP_FUNCTION_NAME = "sample-stepfunction-1"
GET_EXECUTIONS_METHOD_NAME = "lib.metrics_extractor.step_functions_metrics_extractor.StepFunctionsManager.get_step_function_executions"

EXEC_SUCCESS = ExecutionData(
    executionArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:{STEP_FUNCTION_NAME}:f290f993-bda9-dbdf-blablabla",
    stateMachineArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:{STEP_FUNCTION_NAME}",
    name="f290f993-bda9-dbdf-blablabla",
    status="SUCCEEDED",
    startDate=datetime(2024, 1, 1, 0, 0, 0),
    stopDate=datetime(2024, 1, 1, 0, 0, 5),
)

EXEC_SUCCESS2 = ExecutionData(
    executionArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:{STEP_FUNCTION_NAME}:f0000000-bda9-dbdf-blablabla",
    stateMachineArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:{STEP_FUNCTION_NAME}",
    name="f0000000-bda9-dbdf-blablabla",
    status="SUCCEEDED",
    startDate=datetime(2024, 1, 1, 0, 0, 0),
    stopDate=datetime(2024, 1, 1, 0, 0, 5),
)

EXEC_FAILED = ExecutionData(
    executionArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:{STEP_FUNCTION_NAME}:f1111111-bda9-dbdf-blablabla",
    stateMachineArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:{STEP_FUNCTION_NAME}",
    name="f1111111-bda9-dbdf-blablabla",
    status="FAILED",
    startDate=datetime(2024, 1, 2, 0, 0, 6),
    stopDate=datetime(2024, 1, 2, 0, 0, 9),
)

EXEC_RUNNING = ExecutionData(
    executionArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:{STEP_FUNCTION_NAME}:f2222222-bda9-dbdf-blablabla",
    stateMachineArn=f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:{STEP_FUNCTION_NAME}",
    name="f2222222-bda9-dbdf-blablabla",
    status="RUNNING",
    startDate=datetime(2024, 1, 2, 0, 0, 10),
    stopDate=datetime(2024, 1, 2, 0, 0, 15),
)

####################################################################

# get_step_function_executions


# here we check number of records returned and fields (dimensions and metric values)
def test_two_completed_records_integrity(boto3_client_creator):
    # explicitly return 2 good records
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_step_function_executions:
        mocked_get_step_function_executions.return_value = [EXEC_SUCCESS, EXEC_SUCCESS2]

        extractor = StepFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="stepfunctions",
            resource_name=STEP_FUNCTION_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["step_function_run_id"]
        required_metrics = [
            "execution",
            "succeeded",
            "failed",
            "duration_sec",
            "error_message",
        ]

        record_in_scope = records[0]

        mocked_get_step_function_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be two run records"  # we got both records

        assert contains_required_items(
            record_in_scope, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_in_scope, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


# here we check number of records returned
def test_skip_running_execution(boto3_client_creator):
    # explicitly return 2 good records, (1 is not completed)
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_step_function_executions:
        mocked_get_step_function_executions.return_value = [EXEC_SUCCESS, EXEC_RUNNING]

        extractor = StepFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="stepfunctions",
            resource_name=STEP_FUNCTION_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        mocked_get_step_function_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 1
        ), "There should be just one execution record"  # we only take completed executions


# here we check handling failed jobs
def test_failed_job_and_error(boto3_client_creator):
    get_execution_error_method_name = "lib.metrics_extractor.step_functions_metrics_extractor.StepFunctionsManager.get_execution_error"

    # explicitly return 2 good records, (1 is not completed)
    with patch(
        GET_EXECUTIONS_METHOD_NAME
    ) as mocked_get_step_function_executions, patch(
        get_execution_error_method_name
    ) as mocked_get_execution_error:
        mocked_get_step_function_executions.return_value = [EXEC_SUCCESS, EXEC_FAILED]

        test_error_message = "test error message"
        mocked_get_execution_error.return_value = test_error_message

        extractor = StepFunctionsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="stepfunctions",
            resource_name=STEP_FUNCTION_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        mocked_get_step_function_executions.assert_called_once()  # mocked call executed as expected
        assert len(records) == 2, "There should be just two execution records"
        assert (
            get_measure_value(records[1], "error_message") == test_error_message
        )  # checking error message is populated (for failed execution)
