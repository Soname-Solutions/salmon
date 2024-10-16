import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import LambdaFunctionsEventMapper
from lib.core.constants import EventResult, SettingConfigResourceTypes as types


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_lambda_function_event(event_state=None, event_result=None, event_message=None):
    return {
        "detail-type": "Lambda Function Execution State Change",
        "source": "salmon.lambda",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "lambdaName": "lambda-test",
            "message": event_message,
            "state": event_state,
            "event_result": event_result,
            "origin_account": "0987654321",
            "origin_region": "test-origin-region",
            "request_id": "c12129fe",
            "log_stream": "test-log-stream",
        },
    }


def test_get_execution_info_url(mock_settings):
    event = get_lambda_function_event()
    mapper = LambdaFunctionsEventMapper(
        resource_type=types.LAMBDA_FUNCTIONS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="TestLambda")

    expected_url = "https://test-origin-region.console.aws.amazon.com/cloudwatch/home?region=test-origin-region#logsV2:log-groups/log-group/$252Faws$252Flambda$252FTestLambda/log-events/"
    assert returned_url == expected_url


def test_get_message_body(mock_settings):
    event_state = "SUCCEEDED"
    event_message = "Lambda succeeded"
    event = get_lambda_function_event(
        event_state=event_state,
        event_result=EventResult.SUCCESS,
        event_message=event_message,
    )

    mapper = LambdaFunctionsEventMapper(
        resource_type=types.LAMBDA_FUNCTIONS, event=event, settings=mock_settings
    )
    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]

    expected_table_rows = [
        {"values": ["AWS Account", "0987654321"]},
        {"values": ["AWS Region", "test-origin-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", "Lambda Function Execution State Change"]},
        {"values": ["Function Name", "lambda-test"]},
        {"values": ["State", event_state]},
        {
            "values": [
                "Log Events",
                "<a href='https://test-origin-region.console.aws.amazon.com/cloudwatch/home?region=test-origin-region#logsV2:log-groups/log-group/$252Faws$252Flambda$252Flambda-test/log-events/'>Link to AWS CloudWatch Log Group</a>",
            ]
        },
        {"values": ["Log Stream", "test-log-stream"]},
        {"values": ["Request ID", "c12129fe"]},
        {"values": ["Message", "Lambda succeeded"]},
    ]
    assert returned_table_rows == expected_table_rows
