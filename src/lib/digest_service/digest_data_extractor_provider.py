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
)

from lib.core.constants import SettingConfigResourceTypes as types


class DigestDataExtractorProvider:
    """Metrics extractor provider."""

    _digest_extractors = {}

    @staticmethod
    def register_digest_provider(
        resource_type: str,
        digest_extractor: BaseDigestDataExtractor,
    ):
        """Register metrics extractor."""
        DigestDataExtractorProvider._digest_extractors[resource_type] = digest_extractor

    @staticmethod
    def get_digest_provider(resource_type: str, **kwargs) -> BaseDigestDataExtractor:
        """Get metrics extractor."""
        extractor = DigestDataExtractorProvider._digest_extractors.get(resource_type)

        if not extractor:
            raise ValueError(
                f"Digest extractor for resource type {resource_type} is not registered."
            )

        return extractor(resource_type, **kwargs)


DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.GLUE_JOBS, digest_extractor=GlueJobsDigestDataExtractor
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.GLUE_WORKFLOWS,
    digest_extractor=GlueWorkflowsDigestDataExtractor,
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.GLUE_CRAWLERS, digest_extractor=GlueCrawlersDigestDataExtractor
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.GLUE_DATA_CATALOGS,
    digest_extractor=GlueDataCatalogsDigestDataExtractor,
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.GLUE_DATA_QUALITY,
    digest_extractor=GlueDataQualityDigestDataExtractor,
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.STEP_FUNCTIONS,
    digest_extractor=StepFunctionsDigestDataExtractor,
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.LAMBDA_FUNCTIONS,
    digest_extractor=LambdaFunctionsDigestDataExtractor,
)
DigestDataExtractorProvider.register_digest_provider(
    resource_type=types.EMR_SERVERLESS,
    digest_extractor=EMRServerlessDigestDataExtractor,
)
