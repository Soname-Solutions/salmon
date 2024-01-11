from ..core.constants import SettingConfigResourceTypes as types


class ResourceTypeResolver:
    _source_detail_type_map = {
        "aws.glue": {
            "Job": types.GLUE_JOBS,
            "Workflow": types.GLUE_WORKFLOWS,
            "Data Catalog": types.GLUE_DATA_CATALOGS,
            "Crawler": types.GLUE_CRAWLERS,
        },
        "aws.states": types.STEP_FUNCTIONS,
    }

    @staticmethod
    def resolve(event: dict) -> str:
        source = event["source"]
        detail_type = event["detail-type"]

        source_resource_type = ResourceTypeResolver._source_detail_type_map[source]

        if isinstance(source_resource_type, str):
            return source_resource_type

        if isinstance(source_resource_type, dict):
            for keyword, resource_type in source_resource_type.items():
                if keyword in detail_type:
                    return resource_type

        raise KeyError(
            f"No event mapper configured for event detail type: {detail_type}"
        )
