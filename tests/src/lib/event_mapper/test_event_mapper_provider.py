import pytest
from unittest.mock import patch

from lib.event_mapper import (
    EventMapperProvider,
    GlueJobEventMapper,
    GlueWorkflowEventMapper,
    GlueCrawlerEventMapper,
    GlueDataCatalogEventMapper,
    StepFunctionsEventMapper,
    LambdaFunctionsEventMapper,
)
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs


TEST_EVENT = {
    "account": "1234567890",
    "region": "test-region",
    "detail": {"origin_account": "0987654321", "origin_region": "origin-test-region"},
}


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


def test_event_mapper_all_resource_types_registered(mock_settings):
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        returned_event_mapper = EventMapperProvider.get_event_mapper(
            resource_type=resource_type, event=TEST_EVENT, settings=mock_settings
        )
        assert (
            returned_event_mapper is not None
        ), f"No event mapper found for resource type {resource_type}"


def test_unregistered_event_mapper():
    with pytest.raises(ValueError):
        EventMapperProvider.get_event_mapper("unregistered_type")


@pytest.mark.parametrize(
    "scenario, resource_type, expected_event_mapper",
    [
        ("scen1", types.GLUE_JOBS, GlueJobEventMapper),
        ("scen2", types.GLUE_WORKFLOWS, GlueWorkflowEventMapper),
        ("scen3", types.GLUE_DATA_CATALOGS, GlueDataCatalogEventMapper),
        ("scen4", types.GLUE_CRAWLERS, GlueCrawlerEventMapper),
        ("scen5", types.LAMBDA_FUNCTIONS, LambdaFunctionsEventMapper),
        ("scen6", types.STEP_FUNCTIONS, StepFunctionsEventMapper),
    ],
)
def test_get_event_mapper(
    scenario, resource_type, expected_event_mapper, mock_settings
):
    returned_event_mapper = EventMapperProvider.get_event_mapper(
        resource_type=resource_type, event=TEST_EVENT, settings=mock_settings
    )
    assert isinstance(returned_event_mapper, expected_event_mapper)
    assert str(expected_event_mapper) in str(type(returned_event_mapper))
