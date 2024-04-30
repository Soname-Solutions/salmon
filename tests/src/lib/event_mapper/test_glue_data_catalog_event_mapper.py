import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import (
    GlueDataCatalogEventMapper,
    GlueDataCatalogEventMapperException,
)
from lib.core.constants import SettingConfigResourceTypes as types

EVENT_TYPE = "Glue Data Catalog Database State Change"


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def get_glue_data_catalog_event(
    event_state=None, detail_type=EVENT_TYPE, typeOfChange=None
):
    return {
        "detail-type": detail_type,
        "source": "aws.glue",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "databaseName": "glue-data-catalog-test",
            "typeOfChange": typeOfChange,
            "state": event_state,
            "changedTables": ["test-table"],
        },
    }


@pytest.mark.parametrize(
    "scenario, event_state, expected_state",
    [
        ("scen1", None, "SUCCESS"),
        ("scen2", "RUNNING", "RUNNING"),
        ("scen3", "FAILED", "FAILED"),
        ("scen4", "SUCCEEDED", "SUCCEEDED"),
    ],
)
def test_get_resource_state(mock_settings, scenario, event_state, expected_state):
    event = get_glue_data_catalog_event(event_state=event_state)
    mapper = GlueDataCatalogEventMapper(
        resource_type=types.GLUE_DATA_CATALOGS, event=event, settings=mock_settings
    )
    assert mapper.get_resource_state() == expected_state


def test_get_resource_state_exception(mock_settings):
    event = get_glue_data_catalog_event(detail_type="test-detail-type")
    mapper = GlueDataCatalogEventMapper(
        resource_type=types.GLUE_DATA_CATALOGS, event=event, settings=mock_settings
    )
    with pytest.raises(GlueDataCatalogEventMapperException):
        mapper.get_resource_state()


@pytest.mark.parametrize(
    "scenario, event_state, typeOfChange,  expected_url",
    [
        (
            "scen1",
            "FAILED",
            "CreateDatabase",
            "https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/databases/view/glue-data-catalog-test",
        ),
        (
            "scen2",
            "RUNNING",
            "CreateTable",
            "https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/tables/view/test-table?database=glue-data-catalog-test",
        ),
    ],
)
def test_get_execution_info_url(
    mock_settings, scenario, event_state, typeOfChange, expected_url
):
    event = get_glue_data_catalog_event(
        event_state=event_state, typeOfChange=typeOfChange
    )
    mapper = GlueDataCatalogEventMapper(
        resource_type=types.GLUE_DATA_CATALOGS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name="glue-data-catalog-test")

    assert returned_url == expected_url


def test_get_execution_info_url_exception(mock_settings):
    event = {
        "account": "test-account",
        "region": "test-region",
    }
    mapper = GlueDataCatalogEventMapper(
        resource_type=types.GLUE_DATA_CATALOGS, event=event, settings=mock_settings
    )
    with pytest.raises(GlueDataCatalogEventMapperException):
        mapper.get_execution_info_url(resource_name="glue-data-catalog-test")


def test_get_message_body(mock_settings):
    event_state = "SUCCEEDED"
    event = get_glue_data_catalog_event(
        event_state=event_state, typeOfChange="CreateDatabase"
    )
    mapper = GlueDataCatalogEventMapper(
        resource_type=types.GLUE_DATA_CATALOGS, event=event, settings=mock_settings
    )

    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]
    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", EVENT_TYPE]},
        {"values": ["Database Name", "glue-data-catalog-test"]},
        {"values": ["Type of Change", "CreateDatabase"]},
        {
            "values": [
                "Execution Info",
                "<a href='https://test-region.console.aws.amazon.com/glue/home?region=test-region#/v2/data-catalog/databases/view/glue-data-catalog-test'>Link to AWS Console</a>",
            ]
        },
    ]
    assert returned_table_rows == expected_table_rows
