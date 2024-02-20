from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.core.constants import SettingConfigs
from lib.aws.aws_naming import AWSNaming
from logging import Logger

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lib.core.constants import SettingConfigResourceTypes as types


class MetricsExtractorException(Exception):
    """Exception raised for errors encountered while processing metrics extraction."""

    pass


def retrieve_last_update_time_for_all_resources(
    query_runner: TimeStreamQueryRunner, timestream_db_name: str, logger: Logger
) -> dict:
    """
    Gets max(time) for each resource_type (from {restype}_metrics table and for each resource_name
    Returns a dict of resource type to last update time for that resource type.

    Sample output:
        {
        "glue_jobs": [
            {
            "resource_name": "glue-salmonts-pyjob-one-dev",
            "last_update_time": "2024-01-09 11:00:40.366000000"
            }
        ],
        "glue_workflows": [
            {
            "resource_name": "glue-salmonts-workflow-dev",
            "last_update_time": "2024-01-09 11:05:37.417000000"
            }
        ]
        }
    """

    table_parts = []
    try:
        for resource_type in SettingConfigs.RESOURCE_TYPES:
            timestream_table_name = AWSNaming.TimestreamMetricsTable(
                None, resource_type
            )

            if not (
                query_runner.is_table_empty(timestream_db_name, timestream_table_name)
            ):
                table_parts.append(
                    f"""SELECT \'{resource_type}\' as resource_type, resource_name, max(time) as last_update_time 
                                         FROM "{timestream_db_name}"."{timestream_table_name}" 
                                        GROUP BY resource_name
                                    """
                )
            else:
                logger.info(f"No data in table {timestream_table_name}, skipping..")

        if not table_parts:  # All metric tables are empty
            return {}

        query = f" UNION ALL ".join(table_parts)
        result = query_runner.execute_query(query)

        # this parts transforms plain resultset, grouping it by resource_type
        transformed_data = {}

        # Iterating through each item in the input JSON
        for item in result:
            resource_type = item["resource_type"]

            # Check if the resource_type already exists in the transformed_data
            if resource_type not in transformed_data:
                transformed_data[resource_type] = []

            # Add the relevant fields to the corresponding resource_type
            transformed_data[resource_type].append(
                {
                    "resource_name": item["resource_name"],
                    "last_update_time": item["last_update_time"],
                }
            )

        return transformed_data
    except Exception as e:
        logger.error(e)
        error_message = f"Error getting last update time : {e}"
        raise MetricsExtractorException(error_message)


def get_last_update_time(
    last_update_time_json: dict, resource_type: str, resource_name: str
) -> str:
    """
    Returns last update time for the given resource type and resource name
    """
    if last_update_time_json is None:
        return None

    resource_type_section = last_update_time_json.get(resource_type)
    if resource_type_section is None:
        return None

    for resource_info in resource_type_section:
        if resource_info["resource_name"] == resource_name:
            datettime_utc = str_utc_datetime_to_datetime(
                resource_info["last_update_time"]
            )
            return datettime_utc

    return None


def get_job_run_url(
    resource_type: str,
    region_name: str,
    resource_name: str,
    account_id: str = None,
    run_id: str = None,
) -> str:
    """Returns the link to the particular resource run."""

    url_mapping = {
        types.GLUE_JOBS: f"https://{region_name}.console.aws.amazon.com/gluestudio/home?region={region_name}#/job/{resource_name}/run/{run_id}",
        types.STEP_FUNCTIONS: f"https://{region_name}.console.aws.amazon.com/states/home?region={region_name}#/v2/executions/details/arn:aws:states:{region_name}:{account_id}:execution:{resource_name}:{run_id}",
        types.LAMBDA_FUNCTIONS: f"https://{region_name}.console.aws.amazon.com/cloudwatch/home?region={region_name}#logsV2:log-groups/log-group/$252Faws$252Flambda$252F{resource_name}/log-events/",
        types.GLUE_CRAWLERS: f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/data-catalog/crawlers/view/{resource_name}",
        types.GLUE_DATA_CATALOGS: f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/data-catalog/databases/view/{resource_name}",
        types.GLUE_WORKFLOWS: f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/etl-configuration/workflows/view/{resource_name}?activeViewTab=id-tab-history",
    }

    return url_mapping.get(resource_type, "")
