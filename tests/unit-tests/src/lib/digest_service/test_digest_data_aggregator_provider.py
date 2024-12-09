import pytest
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs
from lib.digest_service import (
    DigestDataAggregatorProvider,
    DigestDataAggregator,
    GlueCatalogsDigestAggregator,
)


STAGE_NAME = "teststage"


def test_all_resource_types_registered():
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        returned_extractor = DigestDataAggregatorProvider.get_aggregator_provider(
            resource_type=resource_type
        )
        assert (
            returned_extractor is not None
        ), f"No extractor found for resource type {resource_type}"


def test_unregistered_resource_type():
    with pytest.raises(ValueError):
        DigestDataAggregatorProvider.get_aggregator_provider("unregistered_type")


@pytest.mark.parametrize(
    "scenario, resource_type, expected_extractor",
    [
        ("scen1", types.GLUE_JOBS, DigestDataAggregator),
        ("scen2", types.GLUE_WORKFLOWS, DigestDataAggregator),
        ("scen3", types.GLUE_DATA_CATALOGS, GlueCatalogsDigestAggregator),
        ("scen4", types.GLUE_CRAWLERS, DigestDataAggregator),
        ("scen5", types.LAMBDA_FUNCTIONS, DigestDataAggregator),
        ("scen6", types.STEP_FUNCTIONS, DigestDataAggregator),
        ("scen7", types.GLUE_DATA_QUALITY, DigestDataAggregator),
        ("scen8", types.EMR_SERVERLESS, DigestDataAggregator),
    ],
)
def test_get_digest_provider(scenario, resource_type, expected_extractor):
    returned_extractor = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type=resource_type
    )
    assert isinstance(returned_extractor, expected_extractor)
    assert str(expected_extractor) in str(type(returned_extractor))
