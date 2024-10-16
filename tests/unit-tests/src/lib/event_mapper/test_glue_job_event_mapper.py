import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import GlueJobEventMapper
from lib.core.constants import EventResult, SettingConfigResourceTypes as types


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_glue_job_event(event_state=None, event_message=None):
    return {
        "detail-type": "Glue Job State Change",
        "source": "aws.glue",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "message": event_message,
            "jobName": "glue-job-test",
            "jobRunId": "jr_abcdef01",
            "state": event_state,
        },
    }


@pytest.mark.parametrize(
    "scenario, event_state, event_message, expected_event_result",
    [
        ("scen1", "SUCCEEDED", "Glue job succeeded", EventResult.SUCCESS),
        ("scen2", "FAILED", "Glue job failed", EventResult.FAILURE),
        ("scen3", "RUNNING", "Glue job running", EventResult.INFO),
    ],
)
def test_get_event_result(
    mock_settings, scenario, event_state, event_message, expected_event_result
):
    event = get_glue_job_event(event_state=event_state, event_message=event_message)
    mapper = GlueJobEventMapper(
        resource_type=types.GLUE_JOBS, event=event, settings=mock_settings
    )
    assert mapper.get_event_result() == expected_event_result


def test_get_execution_info_url(mock_settings):
    event = get_glue_job_event()
    mapper = GlueJobEventMapper(
        resource_type=types.GLUE_JOBS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="TestGLueJob")

    expected_url = "https://test-region.console.aws.amazon.com/gluestudio/home?region=test-region#/job/TestGLueJob/run/jr_abcdef01"
    assert returned_url == expected_url


def test_get_message_body(mock_settings):
    event_state = "SUCCEEDED"
    event_message = "Glue Job succeeded"
    event = get_glue_job_event(event_state=event_state, event_message=event_message)

    mapper = GlueJobEventMapper(
        resource_type=types.GLUE_JOBS, event=event, settings=mock_settings
    )
    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]

    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", "Glue Job State Change"]},
        {"values": ["Job Name", "glue-job-test"]},
        {"values": ["State", event_state]},
        {
            "values": [
                "Glue Job Run ID",
                "<a href='https://test-region.console.aws.amazon.com/gluestudio/home?region=test-region#/job/glue-job-test/run/jr_abcdef01'>jr_abcdef01</a>",
            ]
        },
        {"values": ["Message", event_message]},
    ]
    assert returned_table_rows == expected_table_rows
