from datetime import datetime

from lib.metrics_extractor import GlueWorkflowsMetricExtractor
from lib.aws.glue_manager import WorkflowRun, WorkflowStatistics

from common import boto3_client_creator, get_measure_value, contains_required_items
from unittest.mock import patch
import pytest

REGION = "us-east-1"
ACCOUNT_ID = "1234567890"
WORKFLOW_NAME = "glue-workflow-1"
GLUE_MANAGER_CLASS_NAME = "lib.metrics_extractor.glue_workflows_metrics_extractor.GlueManager"
GET_EXECUTIONS_METHOD_NAME = f"{GLUE_MANAGER_CLASS_NAME}.get_workflow_runs"

EVENTS_MANAGER_CLASS_NAME = "lib.metrics_extractor.glue_workflows_metrics_extractor.EventsManager"
PUT_EVENTS_METHOD_NAME = f"{EVENTS_MANAGER_CLASS_NAME}.put_events"

EXEC_SUCCESS1 = WorkflowRun(
    Name = WORKFLOW_NAME,
    WorkflowRunId = "wr_cd3af9e5d8cb32e03a56f7143e12e457c124fa628f9e5f88cb9fd4d9d75ac000",
    WorkflowRunProperties = {},
    StartedOn = datetime(2024,1,1,0,0,0),
    CompletedOn = datetime(2024,1,1,0,5,0),
    Status = "COMPLETED",
    Statistics = WorkflowStatistics(
        TotalActions = 5,
        TimeoutActions = 0,
        FailedActions = 0,
        StoppedActions = 0,
        SucceededActions = 5,
        RunningActions = 0,
        ErroredActions = 0,
        WaitingActions = 0,         
    )
)

EXEC_SUCCESS2 = WorkflowRun(
    Name = WORKFLOW_NAME,
    WorkflowRunId = "wr_cd3af9e5d8cb32e03a56f7143e12e457c124fa628f9e5f88cb9fd4d9d75ac111",
    WorkflowRunProperties = {},
    StartedOn = datetime(2024,1,1,0,10,0),
    CompletedOn = datetime(2024,1,1,0,15,0),
    Status = "COMPLETED",
    Statistics = WorkflowStatistics(
        TotalActions = 5,
        TimeoutActions = 0,
        FailedActions = 0,
        StoppedActions = 0,
        SucceededActions = 5,
        RunningActions = 0,
        ErroredActions = 0,
        WaitingActions = 0,         
    )
)

EXEC_FAILED = WorkflowRun(
    Name = WORKFLOW_NAME,
    WorkflowRunId = "wr_cd3af9e5d8cb32e03a56f7143e12e457c124fa628f9e5f88cb9fd4d9d75ac222",
    WorkflowRunProperties = {},
    StartedOn = datetime(2024,1,1,0,15,0),
    CompletedOn = datetime(2024,1,1,0,20,0),
    Status = "COMPLETED",
    Statistics = WorkflowStatistics(
        TotalActions = 5,
        TimeoutActions = 0,
        FailedActions = 2,
        StoppedActions = 0,
        SucceededActions = 0,
        RunningActions = 0,
        ErroredActions = 0,
        WaitingActions = 0,         
    )
)

EXEC_RUNNING = WorkflowRun(
    Name = WORKFLOW_NAME,
    WorkflowRunId = "wr_cd3af9e5d8cb32e03a56f7143e12e457c124fa628f9e5f88cb9fd4d9d75ac333",
    WorkflowRunProperties = {},
    StartedOn = datetime(2024,1,1,0,20,0),
    CompletedOn = datetime(2024,1,1,0,25,0),
    Status = "RUNNING",
    Statistics = WorkflowStatistics(
        TotalActions = 5,
        TimeoutActions = 0,
        FailedActions = 0,
        StoppedActions = 0,
        SucceededActions = 0,
        RunningActions = 0,
        ErroredActions = 0,
        WaitingActions = 0,         
    )
)

####################################################################

# here we check number of records returned and fields (dimensions and metric values)
def test_two_completed_records_integrity(boto3_client_creator):
    
    # explicitly return 2 good records
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [EXEC_SUCCESS1, EXEC_SUCCESS2]

        extractor = GlueWorkflowsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=WORKFLOW_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["workflow_run_id"]
        required_metrics = [
            "execution",
            "succeeded",
            "failed",
            "actions_succeeded",
            "actions_failed",            
            "execution_time_sec",
            "error_message",
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

# here we check number of records returned
def test_skip_running_execution(boto3_client_creator):

    # explicitly return 2 good records, (1 is not completed)
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [EXEC_SUCCESS1, EXEC_RUNNING]

        extractor = GlueWorkflowsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=WORKFLOW_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        mocked_get_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 1
        ), "There should be just one execution record"  # we only take completed executions

# here we check handling failed jobs
# 1. populate metric "failed"
# 2. execute put_events (for sending errors into event bus)
def test_failed_job_and_error(boto3_client_creator):

    # explicitly return 2 good records, (1 is not completed)
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [EXEC_SUCCESS1, EXEC_FAILED]

        extractor = GlueWorkflowsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=WORKFLOW_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(
            since_time=since_time
        )                

        mocked_get_executions.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be just two execution records"  
        assert get_measure_value(records[0], "succeeded") == '1'
        assert get_measure_value(records[0], "failed") == '0'     
        assert get_measure_value(records[1], "succeeded") == '0'
        assert get_measure_value(records[1], "failed") == '1'



# here we check handling failed jobs
def test_send_alerts(boto3_client_creator):
    # explicitly return 2 good records, (1 is not completed)
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [EXEC_SUCCESS1, EXEC_RUNNING, EXEC_FAILED]

        extractor = GlueWorkflowsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=WORKFLOW_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )   

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(
            since_time=since_time
        )             
    
        with patch(PUT_EVENTS_METHOD_NAME) as mocked_put_events:
            alerts_event_bus_name = "dummy_bus_name"
            ret_val = extractor.send_alerts(alerts_event_bus_name, boto3_client_creator.account_id, boto3_client_creator.region)

            mocked_put_events.assert_called_once() # sent alert to eventbus
            assert ret_val["events_sent"] == 2 # Both succeeded and failed events are sent. Running - skipped

