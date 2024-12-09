from lib.digest_service import (
    DigestDataAggregator,
    GlueCatalogsDigestAggregator,
)

from lib.core.constants import SettingConfigResourceTypes as types


class DigestDataAggregatorProvider:
    """Digest aggregator provider."""

    _digest_aggregators = {}

    @staticmethod
    def register_digest_aggregator(
        resource_type: str,
        digest_aggregator: DigestDataAggregator,
    ):
        """Register digest aggregator."""
        DigestDataAggregatorProvider._digest_aggregators[
            resource_type
        ] = digest_aggregator

    @staticmethod
    def get_aggregator_provider(resource_type: str, **kwargs) -> DigestDataAggregator:
        """Get digest aggregator."""
        aggregator = DigestDataAggregatorProvider._digest_aggregators.get(resource_type)

        if not aggregator:
            raise ValueError(
                f"Digest aggregator for resource type {resource_type} is not registered."
            )

        return aggregator(resource_type, **kwargs)


DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.GLUE_DATA_CATALOGS,  # separate aggregation logic only for Glue Data Catalogs
    digest_aggregator=GlueCatalogsDigestAggregator,
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.GLUE_JOBS, digest_aggregator=DigestDataAggregator
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.GLUE_WORKFLOWS,
    digest_aggregator=DigestDataAggregator,
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.GLUE_CRAWLERS, digest_aggregator=DigestDataAggregator
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.GLUE_DATA_QUALITY,
    digest_aggregator=DigestDataAggregator,
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.STEP_FUNCTIONS,
    digest_aggregator=DigestDataAggregator,
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.LAMBDA_FUNCTIONS,
    digest_aggregator=DigestDataAggregator,
)
DigestDataAggregatorProvider.register_digest_aggregator(
    resource_type=types.EMR_SERVERLESS,
    digest_aggregator=DigestDataAggregator,
)
