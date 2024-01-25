from lib.digest_service import (
    BaseDigestDataExtractor,
    GlueJobsDigestDataExtractor,
    StepFunctionsDigestDataExtractor,
)

from lib.core.constants import SettingConfigResourceTypes as types


class DigestDataExtractorProvider:
    """Metrics extractor provider."""

    _digest_extractors = {}

    @staticmethod
    def register_digest_provider(
        service_name: str,
        digest_extractor: BaseDigestDataExtractor,
    ):
        """Register metrics extractor."""
        DigestDataExtractorProvider._digest_extractors[service_name] = digest_extractor

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
    service_name=types.GLUE_JOBS, digest_extractor=GlueJobsDigestDataExtractor
)
DigestDataExtractorProvider.register_digest_provider(
    service_name=types.STEP_FUNCTIONS, digest_extractor=StepFunctionsDigestDataExtractor
)
