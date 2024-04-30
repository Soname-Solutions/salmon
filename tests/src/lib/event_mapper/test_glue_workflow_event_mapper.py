import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import GlueWorkflowEventMapper
from lib.core.constants import EventResult, SettingConfigResourceTypes as types


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_glue_workflow_event(event_state="SUCCEEDED", event_result=EventResult.SUCCESS):
    return {
        "detail-type": "Glue Workflow State Change",
        "source": "salmon.glue_workflow",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "workflowName": "glue-workflow-test",
            "state": event_state,
            "event_result": event_result,
            "origin_account": "0987654321",
            "origin_region": "test-origin-region",
            "workflowRunId": "d12129fe",
        },
    }


@pytest.mark.parametrize(
    "scenario, event_state, event_result, final_state",
    [
        ("scen1", "TIMEOUTED", "FAILURE", "FAILED"),
        ("scen2", "CANCELLING", "STOPPED", "FAILED"),
        ("scen3", "CANCELLED", "ERROR", "FAILED"),
        ("scen4", "SUCCEEDED", "SUCCESS", "SUCCEEDED"),
        ("scen5", "RUNNING", "INFO", "RUNNING"),
    ],
)
def test_get_resource_state(
    mock_settings, scenario, event_state, event_result, final_state
):
    event = get_glue_workflow_event(event_state=event_state, event_result=event_result)
    mapper = GlueWorkflowEventMapper(
        resource_type=types.GLUE_WORKFLOWS, event=event, settings=mock_settings
    )
    assert mapper.get_resource_state() == final_state


def test_get_execution_info_url(mock_settings):
    event = get_glue_workflow_event()
    mapper = GlueWorkflowEventMapper(
        resource_type=types.GLUE_WORKFLOWS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="TestGlueWF")

    expected_url = "https://test-origin-region.console.aws.amazon.com/glue/home?region=test-origin-region#/v2/etl-configuration/workflows/run/TestGlueWF?runId=d12129fe"
    assert returned_url == expected_url


def test_get_message_body(mock_settings):
    event = get_glue_workflow_event()
    mapper = GlueWorkflowEventMapper(
        resource_type=types.GLUE_WORKFLOWS, event=event, settings=mock_settings
    )
    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]

    expected_table_rows = [
        {"values": ["AWS Account", "0987654321"]},
        {"values": ["AWS Region", "test-origin-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", "Glue Workflow State Change"]},
        {"values": ["Workflow Name", "glue-workflow-test"]},
        {
            "values": [
                "Workflow Run ID",
                "<a href='https://test-origin-region.console.aws.amazon.com/glue/home?region=test-origin-region#/v2/etl-configuration/workflows/run/glue-workflow-test?runId=d12129fe'>d12129fe</a>",
            ]
        },
    ]
    assert returned_table_rows == expected_table_rows
