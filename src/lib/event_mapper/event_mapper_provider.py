from lib.event_mapper import (
    GeneralAwsEventMapper,
    GlueJobEventMapper,
    GlueWorkflowEventMapper,
    GlueCrawlerEventMapper,
    GlueDataCatalogEventMapper,
    GlueDataQualityEventMapper,
    StepFunctionsEventMapper,
    LambdaFunctionsEventMapper,
)
from lib.core.constants import SettingConfigResourceTypes as types


class EventMapperProvider:
    """Event Mapper Provider"""

    _event_mappers = {}

    @staticmethod
    def register_event_mapper(resource_type: str, event_mapper: GeneralAwsEventMapper):
        """Register metrics extractor."""
        EventMapperProvider._event_mappers[resource_type] = event_mapper

    @staticmethod
    def get_event_mapper(resource_type: str, **kwargs) -> GeneralAwsEventMapper:
        """Get event mapper."""
        mapper = EventMapperProvider._event_mappers.get(resource_type)

        if not mapper:
            raise ValueError(
                f"Event Mapper for resource type {resource_type} is not registered."
            )

        return mapper(resource_type, **kwargs)


EventMapperProvider.register_event_mapper(types.GLUE_JOBS, GlueJobEventMapper)
EventMapperProvider.register_event_mapper(types.GLUE_WORKFLOWS, GlueWorkflowEventMapper)
EventMapperProvider.register_event_mapper(types.GLUE_CRAWLERS, GlueCrawlerEventMapper)
EventMapperProvider.register_event_mapper(
    types.GLUE_DATA_CATALOGS, GlueDataCatalogEventMapper
)
EventMapperProvider.register_event_mapper(
    types.GLUE_DATA_QUALITY, GlueDataQualityEventMapper
)
EventMapperProvider.register_event_mapper(
    types.STEP_FUNCTIONS, StepFunctionsEventMapper
)
EventMapperProvider.register_event_mapper(
    types.LAMBDA_FUNCTIONS, LambdaFunctionsEventMapper
)
