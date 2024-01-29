from lib.metrics_extractor import (
    BaseMetricsExtractor,
    GlueJobsMetricExtractor,
    GlueWorkflowsMetricExtractor,
    GlueCatalogsMetricExtractor,
    GlueCrawlersMetricExtractor,
    LambdaFunctionsMetricExtractor,
    StepFunctionsMetricExtractor,
)

from lib.core.constants import SettingConfigResourceTypes as types


class MetricsExtractorProvider:
    """Metrics extractor provider."""

    _metrics_extractors = {}

    @staticmethod
    def register_metrics_extractor(
        service_name: str, metrics_extractor: BaseMetricsExtractor
    ):
        """Register metrics extractor."""
        MetricsExtractorProvider._metrics_extractors[service_name] = metrics_extractor

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
    types.GLUE_JOBS, GlueCatalogsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.GLUE_WORKFLOWS, GlueCrawlersMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.LAMBDA_FUNCTIONS, LambdaFunctionsMetricExtractor
)
MetricsExtractorProvider.register_metrics_extractor(
    types.STEP_FUNCTIONS, StepFunctionsMetricExtractor
)
