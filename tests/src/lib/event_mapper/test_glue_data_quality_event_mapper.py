import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import (
    GlueDataQualityEventMapper,
    GlueDataQualityEventMapperException,
)
from lib.core.constants import SettingConfigResourceTypes as types

EVENT_TYPE = "Data Quality Evaluation Results Availablee"
DQ_RULESET_NAME = "glue-dq-ruleset-test"
JOB_NAME = "glue-dq-job-test"
TABLE_NAME = "glue-dq-table-test"
DB_NAME = "glue-dq-db-test"


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_glue_dq_event(
    event_state="SUCCEEDED", detail_type=EVENT_TYPE, contextType=None
):
    return {
        "detail-type": detail_type,
        "source": "aws.glue-dataquality",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "rulesetNames": [DQ_RULESET_NAME],
            "state": event_state,
            "context": {
                "catalogId": "1234567890",
                "contextType": contextType,
                "databaseName": DB_NAME,
                "tableName": TABLE_NAME,
                "jobName": JOB_NAME,
                "jobId": "jr_13969dc14d4d4e99c5db7f4cc68e2c7e3d55719b822e0fdde07f5257905f37bf",
                "runId": "dqrun-823d27d644915f91833172789d4f3c9cc705d90d",
            },
        },
    }


def test_get_resource_name_success(mock_settings):
    event = get_glue_dq_event()
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )
    assert mapper.get_resource_name() == DQ_RULESET_NAME


@pytest.mark.parametrize(
    "scenario, event",
    [
        (
            "scen1-missing-rulesetNames-key",
            {"account": "1234567890", "region": "test-region", "detail": {}},
        ),
        (
            "scen2-empty-rulesetNames-list",
            {
                "account": "1234567890",
                "region": "test-region",
                "detail": {"rulesetNames": []},
            },
        ),
        (
            "scen3-missing-detail-key",
            {
                "account": "1234567890",
                "region": "test-region",
            },
        ),
    ],
)
def test_get_resource_name_exception(mock_settings, scenario, event):
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )
    with pytest.raises(
        GlueDataQualityEventMapperException,
        match=f"Required GLue DQ Ruleset name is not defined in the DQ event",
    ):
        mapper.get_resource_name()


@pytest.mark.parametrize(
    "scenario, event_state, expected_state",
    [
        ("scen1", "RUNNING", "RUNNING"),
        ("scen2", "FAILED", "FAILED"),
        ("scen3", "SUCCEEDED", "SUCCEEDED"),
    ],
)
def test_get_resource_state(mock_settings, scenario, event_state, expected_state):
    event = get_glue_dq_event(event_state=event_state)
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )
    assert (
        mapper.get_resource_state() == expected_state
    ), f"Mismatch for scenario {scenario}"


@pytest.mark.parametrize(
    "scenario, event_state, contextType, expected_url",
    [
        (
            "scen1",
            "FAILED",
            "GLUE_JOB",
            "https://test-region.console.aws.amazon.com/gluestudio/home?region=test-region#/editor/job/glue-dq-job-test/dataquality",
        ),
        (
            "scen2",
            "RUNNING",
            "GLUE_DATA_CATALOG",
            "https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/tables/evaluation-run-details/glue-dq-table-test?database=glue-dq-db-test&catalogId=1234567890&runid=dqrun-823d27d644915f91833172789d4f3c9cc705d90d",
        ),
    ],
)
def test_get_execution_info_url(
    mock_settings, scenario, event_state, contextType, expected_url
):
    event = get_glue_dq_event(event_state=event_state, contextType=contextType)
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name=DQ_RULESET_NAME)

    assert returned_url == expected_url, f"Mismatch for scenario {scenario}"


def test_get_message_body(mock_settings):
    event_state = "SUCCEEDED"
    event = get_glue_dq_event(event_state=event_state, contextType="GLUE_JOB")
    mapper = GlueDataQualityEventMapper(
        resource_type=types.GLUE_DATA_QUALITY, event=event, settings=mock_settings
    )

    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]
    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", EVENT_TYPE]},
        {"values": ["Glue DQ Ruleset Name", DQ_RULESET_NAME]},
        {"values": ["State", event_state]},
        {"values": ["Glue Job Name", JOB_NAME]},
        {
            "values": [
                "Glue DQ Run ID",
                "<a href='https://test-region.console.aws.amazon.com/gluestudio/home?region=test-region#/editor/job/glue-dq-job-test/dataquality'>jr_13969dc14d4d4e99c5db7f4cc68e2c7e3d55719b822e0fdde07f5257905f37bf</a>",
            ]
        },
    ]
    assert returned_table_rows == expected_table_rows
