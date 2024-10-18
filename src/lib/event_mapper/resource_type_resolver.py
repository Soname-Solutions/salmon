from lib.core.constants import SettingConfigResourceTypes as types


class ResourceTypeResolver:
    _source_detail_type_map = {
        "aws.glue": {
            "Glue Job State Change": types.GLUE_JOBS,
            # "Workflow": types.GLUE_WORKFLOWS, # AWS doesn't send EventBridge event yet
            "Glue Data Catalog Database State Change": types.GLUE_DATA_CATALOGS,
            "Glue Data Catalog Table State Change": types.GLUE_DATA_CATALOGS,
            "Glue Crawler State Change": types.GLUE_CRAWLERS,
        },
        "aws.glue-dataquality": {
            "Data Quality Evaluation Results Available": types.GLUE_DATA_QUALITY
        },
        "aws.states": {"Step Functions Execution Status Change": types.STEP_FUNCTIONS},
        "aws.emr-serverless": {
            "EMR Serverless Job Run State Change": types.EMR_SERVERLESS
        },
        "salmon.glue_workflow": {
            "Glue Workflow State Change": types.GLUE_WORKFLOWS
        },  # custom processing
        "salmon.lambda": {
            "Lambda Function Execution State Change": types.LAMBDA_FUNCTIONS
        },  # custom processing
    }

    @staticmethod
    def resolve(event: dict) -> str:
        source = event["source"]
        detail_type = event["detail-type"]

        detail_keyword_resource_type_map = ResourceTypeResolver._source_detail_type_map[
            source
        ]
        resource_type = detail_keyword_resource_type_map.get(detail_type)

        return resource_type
