from unittest.mock import patch
from datetime import datetime, timezone

from lib.aws.lambda_manager import (
    LambdaManager,
    LambdaExecution,
)

SINCE_TIME = datetime(2024, 1, 1, 0, 0, 0)
LAMBDA_NAME = "test-lambda"
REQUEST_ID_ONE = "request-id-1"
LOG_STREAM_ONE = "Stream1"
REQUEST_ID_TWO = "request-id-2"
LOG_STREAM_TWO = "Stream2"


@patch("lib.aws.cloudwatch_manager.CloudWatchManager")
@patch("boto3.client")
def test_get_lambda_success_execution(mock_boto3, mock_cw_man):
    lambda_logs = [
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:25.893"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"START RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"END RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {
                "field": "@message",
                "value": f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            },
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
    ]
    mock_cw_man.query_logs.return_value = lambda_logs

    lambda_man = LambdaManager()
    lambda_executions = lambda_man.get_lambda_runs(
        cloudwatch_manager=mock_cw_man, function_name=LAMBDA_NAME, since_time=SINCE_TIME
    )

    expected_results = [
        LambdaExecution(
            LambdaName=LAMBDA_NAME,
            LogStream=LOG_STREAM_ONE,
            RequestId=REQUEST_ID_ONE,
            Status=LambdaManager.LAMBDA_SUCCESS_STATE,
            Report=f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            Errors=[],
            StartedOn=datetime(2024, 9, 30, 9, 41, 25, 893000, tzinfo=timezone.utc),
            CompletedOn=datetime(2024, 9, 30, 9, 41, 28, 660000, tzinfo=timezone.utc),
        )
    ]

    assert lambda_executions == expected_results
    assert lambda_executions[0].IsFinalState == True
    assert lambda_executions[0].IsSuccess == True
    assert lambda_executions[0].IsFailure == False
    assert lambda_executions[0].Duration == 2758.71
    assert lambda_executions[0].BilledDuration == 2759
    assert lambda_executions[0].MemorySize == 128
    assert lambda_executions[0].MaxMemoryUsed == 80
    assert lambda_executions[0].ErrorString == None


@patch("lib.aws.cloudwatch_manager.CloudWatchManager")
@patch("boto3.client")
def test_get_lambda_failed_execution(mock_boto3, mock_cw_man):
    error_msg_1 = "[ERROR] Exception: intentional failure - lambda dq\n"
    # test Error entry as per the pattern '[ERROR] <timestamp> <request_id> <error_message>'
    error_msg_2 = f"[ERROR]\t2024-09-30T09:41:25.895Z\t{REQUEST_ID_TWO}\tSecond failure - lambda dq\n"

    lambda_logs = [
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:25.893"},
            {"field": "@logStream", "value": LOG_STREAM_TWO},
            {"field": "@message", "value": f"START RequestId: {REQUEST_ID_TWO}\n"},
            {"field": "@requestId", "value": REQUEST_ID_TWO},
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:25.894"},
            {"field": "@logStream", "value": LOG_STREAM_TWO},
            {"field": "@message", "value": error_msg_1},
            {
                "field": "@requestId",
                "value": None,
            },  # RequestID not assigned for ERROR entry in this case
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:25.895"},
            {"field": "@logStream", "value": LOG_STREAM_TWO},
            {"field": "@message", "value": error_msg_2},
            {"field": "@requestId", "value": REQUEST_ID_TWO},
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_TWO},
            {"field": "@message", "value": f"END RequestId: {REQUEST_ID_TWO}\n"},
            {"field": "@requestId", "value": REQUEST_ID_TWO},
        ],
        [
            {"field": "@timestamp", "value": "2024-09-30 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_TWO},
            {
                "field": "@message",
                "value": f"REPORT RequestId: {REQUEST_ID_TWO}\tDuration: 3758.71 ms\tBilled Duration: 3759 ms\tMemory Size: 128 MB\tMax Memory Used: 30 MB\tInit Duration: 361.91 ms\t\n",
            },
            {"field": "@requestId", "value": REQUEST_ID_TWO},
        ],
    ]
    mock_cw_man.query_logs.return_value = lambda_logs

    lambda_man = LambdaManager()
    lambda_executions = lambda_man.get_lambda_runs(
        cloudwatch_manager=mock_cw_man, function_name=LAMBDA_NAME, since_time=SINCE_TIME
    )

    expected_results = [
        LambdaExecution(
            LambdaName=LAMBDA_NAME,
            LogStream=LOG_STREAM_TWO,
            RequestId=REQUEST_ID_TWO,
            Status=LambdaManager.LAMBDA_FAILURE_STATE,
            Report=f"REPORT RequestId: {REQUEST_ID_TWO}\tDuration: 3758.71 ms\tBilled Duration: 3759 ms\tMemory Size: 128 MB\tMax Memory Used: 30 MB\tInit Duration: 361.91 ms\t\n",
            Errors=[error_msg_1, error_msg_2],
            StartedOn=datetime(2024, 9, 30, 9, 41, 25, 893000, tzinfo=timezone.utc),
            CompletedOn=datetime(2024, 9, 30, 9, 41, 28, 660000, tzinfo=timezone.utc),
        )
    ]

    assert lambda_executions == expected_results
    assert lambda_executions[0].IsFinalState == True
    assert lambda_executions[0].IsSuccess == False
    assert lambda_executions[0].IsFailure == True
    assert lambda_executions[0].Duration == 3758.71
    assert lambda_executions[0].BilledDuration == 3759
    assert lambda_executions[0].MemorySize == 128
    assert lambda_executions[0].MaxMemoryUsed == 30
    assert (
        lambda_executions[0].ErrorString
        == "[ERROR] Exception: intentional failure - lambda dq\n; Second failure - lambda dq"
    )  # Errors concatinated as expected


# In case of retry Lambda will log events in the same log stream and under the same request ID
# Check that for each Lambda invocation/retry, a separate LambdaExecution record will be created
@patch("lib.aws.cloudwatch_manager.CloudWatchManager")
@patch("boto3.client")
def test_get_two_lambda_executions_with_same_request_id(mock_boto3, mock_cw_man):
    lambda_logs = [
        [
            {"field": "@timestamp", "value": "2024-10-01 09:41:25.893"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"START RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-10-01 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"END RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-10-01 09:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {
                "field": "@message",
                "value": f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            },
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-10-01 10:41:25.893"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"START RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-10-01 10:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {"field": "@message", "value": f"END RequestId: {REQUEST_ID_ONE}\n"},
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
        [
            {"field": "@timestamp", "value": "2024-10-01 10:41:28.660"},
            {"field": "@logStream", "value": LOG_STREAM_ONE},
            {
                "field": "@message",
                "value": f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            },
            {"field": "@requestId", "value": REQUEST_ID_ONE},
        ],
    ]
    mock_cw_man.query_logs.return_value = lambda_logs

    lambda_man = LambdaManager()
    lambda_executions = lambda_man.get_lambda_runs(
        cloudwatch_manager=mock_cw_man, function_name=LAMBDA_NAME, since_time=SINCE_TIME
    )

    expected_results = [
        LambdaExecution(
            LambdaName=LAMBDA_NAME,
            LogStream=LOG_STREAM_ONE,
            RequestId=REQUEST_ID_ONE,
            Status=LambdaManager.LAMBDA_SUCCESS_STATE,
            Report=f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            Errors=[],
            StartedOn=datetime(2024, 10, 1, 9, 41, 25, 893000, tzinfo=timezone.utc),
            CompletedOn=datetime(2024, 10, 1, 9, 41, 28, 660000, tzinfo=timezone.utc),
        ),
        LambdaExecution(
            LambdaName=LAMBDA_NAME,
            LogStream=LOG_STREAM_ONE,
            RequestId=REQUEST_ID_ONE,
            Status=LambdaManager.LAMBDA_SUCCESS_STATE,
            Report=f"REPORT RequestId: {REQUEST_ID_ONE}\tDuration: 2758.71 ms\tBilled Duration: 2759 ms\tMemory Size: 128 MB\tMax Memory Used: 80 MB\tInit Duration: 261.91 ms\t\n",
            Errors=[],
            StartedOn=datetime(2024, 10, 1, 10, 41, 25, 893000, tzinfo=timezone.utc),
            CompletedOn=datetime(2024, 10, 1, 10, 41, 28, 660000, tzinfo=timezone.utc),
        ),
    ]

    assert len(expected_results) == 2
    assert lambda_executions == expected_results
