from datetime import datetime
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.core.constants import SettingConfigs
from lib.aws.aws_naming import AWSNaming
from lib.aws import TimestreamTableWriter
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


def get_resource_last_update_time(
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


def get_earliest_last_update_time_for_resource_set(
    last_update_times: list,
    resource_names: list,
    timestream_writer: TimestreamTableWriter,
) -> datetime:
    """
    Returns the earliest update time for the specified resources.
    """
    if last_update_times:
        resources_dict = {
            item["resource_name"]: item["last_update_time"]
            for item in last_update_times
        }

        # Check if all resources have last_update_time assigned and get the min date
        if all(resource in resources_dict for resource in resource_names):
            update_times = [
                str_utc_datetime_to_datetime(resources_dict[resource])
                for resource in resource_names
            ]
            return min(update_times)
    # If not all resources exist, get earliest writable time
    return timestream_writer.get_earliest_writeable_time_for_table()
