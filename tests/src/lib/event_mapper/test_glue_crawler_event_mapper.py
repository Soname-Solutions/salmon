import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import GlueCrawlerEventMapper
from lib.core.constants import EventResult, SettingConfigResourceTypes as types


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_glue_crawler_event(event_state=None, event_message=None):
    return {
        "detail-type": "Glue Crawler State Change",
        "source": "aws.glue",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "message": event_message,
            "crawlerName": "glue-crawler-test",
            "state": event_state,
        },
    }


@pytest.mark.parametrize(
    "scenario, event_state, event_message, expected_event_result",
    [
        ("scen1", "Succeeded", "Glue Crawler succeeded", EventResult.SUCCESS),
        ("scen2", "Failed", "Glue Crawler failed", EventResult.FAILURE),
        ("scen3", "Running", "Glue Crawler running", EventResult.INFO),
    ],
)
def test_get_event_result(
    mock_settings, scenario, event_state, event_message, expected_event_result
):
    event = get_glue_crawler_event(event_state=event_state, event_message=event_message)
    mapper = GlueCrawlerEventMapper(
        resource_type=types.GLUE_CRAWLERS, event=event, settings=mock_settings
    )
    assert mapper.get_event_result() == expected_event_result


def test_get_execution_info_url(mock_settings):
    event = get_glue_crawler_event()
    mapper = GlueCrawlerEventMapper(
        resource_type=types.GLUE_CRAWLERS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="TestCrawler")

    expected_url = "https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/crawlers/view/TestCrawler"
    assert returned_url == expected_url


def test_get_message_body(mock_settings):
    event_state = "Failed"
    event_message = "Crawler execution failed"
    event = get_glue_crawler_event(event_state=event_state, event_message=event_message)

    mapper = GlueCrawlerEventMapper(
        resource_type=types.GLUE_CRAWLERS, event=event, settings=mock_settings
    )
    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]

    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", "Glue Crawler State Change"]},
        {"values": ["Crawler Name", "glue-crawler-test"]},
        {
            "values": ["State", event_state],
            "style": "error",
        },  # error style applied as expected
        {
            "values": [
                "Execution Info",
                "<a href='https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/crawlers/view/glue-crawler-test'>Link to AWS Console</a>",
            ]
        },
        {"values": ["Message", event_message]},
    ]
    assert returned_table_rows == expected_table_rows
