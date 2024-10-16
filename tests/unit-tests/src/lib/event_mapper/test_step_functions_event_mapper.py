import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from lib.event_mapper import StepFunctionsEventMapper
from lib.core.constants import EventResult, SettingConfigResourceTypes as types


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_step_function_event(event_state=None):
    test_time = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    time_str = str(test_time)
    epoch_time_ms = int(test_time.timestamp()) * 1000

    return {
        "detail-type": "Step Functions Execution Status Change",
        "source": "aws.states",
        "account": "1234567890",
        "time": time_str,
        "region": "test-region",
        "detail": {
            "name": "6e60909a",
            "stateMachineArn": f"arn:aws:states:test-region:1234567890:stateMachine:stepfunction-test",
            "status": event_state,
            "startDate": epoch_time_ms,
            "stopDate": epoch_time_ms,
        },
    }


@pytest.mark.parametrize(
    "scenario, event_state, expected_event_result",
    [
        ("scen1", "SUCCEEDED", EventResult.SUCCESS),
        ("scen2", "FAILED", EventResult.FAILURE),
        ("scen3", "RUNNING", EventResult.INFO),
    ],
)
def test_get_event_result_success(
    mock_settings, scenario, event_state, expected_event_result
):
    event = get_step_function_event(event_state=event_state)
    mapper = StepFunctionsEventMapper(
        resource_type=types.STEP_FUNCTIONS, event=event, settings=mock_settings
    )
    assert mapper.get_event_result() == expected_event_result


def test_get_execution_info_url(mock_settings):
    event = get_step_function_event()
    mapper = StepFunctionsEventMapper(
        resource_type=types.STEP_FUNCTIONS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="TestStepFunction")

    expected_url = "https://test-region.console.aws.amazon.com/states/home?region=test-region#/v2/executions/details/arn:aws:states:test-region:1234567890:execution:TestStepFunction:6e60909a"
    assert returned_url == expected_url


def test_get_message_body(mock_settings):
    event_state = "SUCCEEDED"
    event = get_step_function_event(event_state=event_state)
    mapper = StepFunctionsEventMapper(
        resource_type=types.STEP_FUNCTIONS, event=event, settings=mock_settings
    )

    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]

    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00+00:00"]},
        {"values": ["Event Type", "Step Functions Execution Status Change"]},
        {"values": ["State Machine Name", "stepfunction-test"]},
        {"values": ["Status", event_state]},
        {"values": ["Start Date", "2000-01-01T00:00:00+00:00"]},
        {"values": ["Stop Date", "2000-01-01T00:00:00+00:00"]},
        {
            "values": [
                "Execution Info",
                "<a href='https://test-region.console.aws.amazon.com/states/home?region=test-region#/v2/executions/details/arn:aws:states:test-region:1234567890:execution:stepfunction-test:6e60909a'>6e60909a</a>",
            ]
        },
    ]
    assert returned_table_rows == expected_table_rows
