from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.core.constants import SettingConfigs
from lib.aws.aws_naming import AWSNaming
from logging import Logger

from lib.core.datetime_utils import str_utc_datetime_to_datetime


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
    output_dict = {}
    for resource_type in SettingConfigs.RESOURCE_TYPES:
        timestream_table_name = AWSNaming.TimestreamMetricsTable(None, resource_type)

        try:
            if not (
                query_runner.is_table_empty(timestream_db_name, timestream_table_name)
            ):
                query = f'SELECT resource_name, max(time) as last_update_time FROM "{timestream_db_name}"."{timestream_table_name}" GROUP BY resource_name'

                result = query_runner.execute_query(query)
                output_dict[resource_type] = result
            else:
                logger.info(f"No data in table {timestream_table_name}, skipping..")
                output_dict[resource_type] = {}

        except Exception as e:
            logger.error(e)
            error_message = f"Error getting last update time : {e}"
            raise MetricsExtractorException(error_message)

    return output_dict


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
