from lib.metrics_extractor import (
    BaseMetricsExtractor,
    GlueJobsMetricExtractor,
    GlueWorkflowsMetricExtractor,
    GlueCatalogsMetricExtractor,
    GlueCrawlersMetricExtractor,
    GlueDataQualityMetricExtractor,
    LambdaFunctionsMetricExtractor,
    StepFunctionsMetricExtractor,
)

from lib.core.constants import SettingConfigResourceTypes as types


class MetricsExtractorProvider:
    """Metrics extractor provider."""

    _metrics_extractors = {}

    @staticmethod
    def register_metrics_extractor(
        resource_type: str, metrics_extractor: BaseMetricsExtractor
    ):
        """Register metrics extractor."""
        MetricsExtractorProvider._metrics_extractors[resource_type] = metrics_extractor

    @staticmethod
    def get_metrics_extractor(resource_type: str, **kwargs) -> BaseMetricsExtractor:
        """Get metrics extractor."""
        extractor = MetricsExtractorProvider._metrics_extractors.get(resource_type)

        if not extractor:
            raise ValueError(
                f"Metrics extractor for resource type {resource_type} is not registered."
            )

        return extractor(**kwargs)


MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_JOBS, GlueJobsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_WORKFLOWS, GlueWorkflowsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_DATA_CATALOGS, GlueCatalogsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_CRAWLERS, GlueCrawlersMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_DATA_QUALITY, GlueDataQualityMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.LAMBDA_FUNCTIONS, LambdaFunctionsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.STEP_FUNCTIONS, StepFunctionsMetricExtractor
)
