from unittest.mock import MagicMock
import pytest
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs
from lib.digest_service import (
    BaseDigestDataExtractor,
    GlueJobsDigestDataExtractor,
    GlueWorkflowsDigestDataExtractor,
    GlueCrawlersDigestDataExtractor,
    GlueDataCatalogsDigestDataExtractor,
    GlueDataQualityDigestDataExtractor,
    StepFunctionsDigestDataExtractor,
    LambdaFunctionsDigestDataExtractor,
    EMRServerlessDigestDataExtractor,
    DigestDataExtractorProvider,
)

from lib.metrics_storage import MetricsStorageTypes

STAGE_NAME = "teststage"


@pytest.fixture
def mocked_metrics_storage():
    return MagicMock()


def test_all_resource_types_registered(mocked_metrics_storage):
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        returned_extractor = DigestDataExtractorProvider.get_digest_provider(
            resource_type=resource_type,
            metrics_storage=mocked_metrics_storage,
        )
        assert (
            returned_extractor is not None
        ), f"No extractor found for resource type {resource_type}"


def test_unregistered_resource_type(mocked_metrics_storage):
    with pytest.raises(ValueError):
        DigestDataExtractorProvider.get_digest_provider(
            resource_type="unregistered_type", metrics_storage=mocked_metrics_storage
        )


@pytest.mark.parametrize(
    "scenario, resource_type, expected_extractor",
    [
        ("scen1", types.GLUE_JOBS, GlueJobsDigestDataExtractor),
        ("scen2", types.GLUE_WORKFLOWS, GlueWorkflowsDigestDataExtractor),
        ("scen3", types.GLUE_DATA_CATALOGS, GlueDataCatalogsDigestDataExtractor),
        ("scen4", types.GLUE_CRAWLERS, GlueCrawlersDigestDataExtractor),
        ("scen5", types.LAMBDA_FUNCTIONS, LambdaFunctionsDigestDataExtractor),
        ("scen6", types.STEP_FUNCTIONS, StepFunctionsDigestDataExtractor),
        ("scen7", types.GLUE_DATA_QUALITY, GlueDataQualityDigestDataExtractor),
        ("scen8", types.EMR_SERVERLESS, EMRServerlessDigestDataExtractor),
    ],
)
def test_get_digest_provider(
    scenario, resource_type, expected_extractor, mocked_metrics_storage
):
    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        metrics_storage=mocked_metrics_storage,
    )
    assert isinstance(returned_extractor, expected_extractor)
    assert str(expected_extractor) in str(type(returned_extractor))
