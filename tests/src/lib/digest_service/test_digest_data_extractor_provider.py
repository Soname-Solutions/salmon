import pytest
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs
from lib.digest_service import (
    BaseDigestDataExtractor,
    GlueJobsDigestDataExtractor,
    GlueWorkflowsDigestDataExtractor,
    GlueCrawlersDigestDataExtractor,
    GlueDataCatalogsDigestDataExtractor,
    StepFunctionsDigestDataExtractor,
    LambdaFunctionsDigestDataExtractor,
    DigestDataExtractorProvider,
)


STAGE_NAME = "teststage"


def test_all_resource_types_registered():
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
        timestream_table_name = f"tstable-{resource_type}-metrics"

        returned_extractor = DigestDataExtractorProvider.get_digest_provider(
            resource_type=resource_type,
            timestream_db_name=timestream_db_name,
            timestream_table_name=timestream_table_name,
        )
        assert (
            returned_extractor is not None
        ), f"No extractor found for resource type {resource_type}"


def test_unregistered_resource_type():
    with pytest.raises(ValueError):
        DigestDataExtractorProvider.get_digest_provider("unregistered_type")


@pytest.mark.parametrize(
    "scenario, resource_type, expected_extractor",
    [
        ("scen1", types.GLUE_JOBS, GlueJobsDigestDataExtractor),
        ("scen2", types.GLUE_WORKFLOWS, GlueWorkflowsDigestDataExtractor),
        ("scen3", types.GLUE_DATA_CATALOGS, GlueDataCatalogsDigestDataExtractor),
        ("scen4", types.GLUE_CRAWLERS, GlueCrawlersDigestDataExtractor),
        ("scen5", types.LAMBDA_FUNCTIONS, LambdaFunctionsDigestDataExtractor),
        ("scen6", types.STEP_FUNCTIONS, StepFunctionsDigestDataExtractor),
    ],
)
def test_get_digest_provider(scenario, resource_type, expected_extractor):
    timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    timestream_table_name = f"tstable-{resource_type}-metrics"

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        timestream_db_name=timestream_db_name,
        timestream_table_name=timestream_table_name,
    )
    assert isinstance(returned_extractor, expected_extractor)
    assert str(expected_extractor) in str(type(returned_extractor))
