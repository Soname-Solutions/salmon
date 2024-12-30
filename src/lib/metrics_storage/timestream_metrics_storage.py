from datetime import datetime
from functools import cached_property
import boto3
from lib.aws.timestream_manager import TimestreamTableWriter, TimeStreamQueryRunner
from lib.settings.settings import SettingConfigs
from lib.aws.aws_naming import AWSNaming
from lib.core.datetime_utils import str_utc_datetime_to_datetime

from lib.metrics_storage.base_metrics_storage import (
    BaseMetricsStorage,
    MetricsStorageException,
)


class TimestreamMetricsStorage(BaseMetricsStorage):
    """
    A proxy class for TimestreamTableWriter and TimeStreamQueryRunner to provide a unified interface for interacting
    with Timestream metrics storage. Clients and writer are lazily initialized to optimize for partial use cases.
    """

    def __init__(self, db_name: str, write_client=None, query_client=None):
        """
        Initialize the TimestreamMetricsStorage.

        Args:
            db_name (str): Name of the Timestream database.
            write_client: Optional boto3 Timestream write client. Lazily initialized if not provided.
            query_client: Optional boto3 Timestream query client. Lazily initialized if not provided.
        """
        self.db_name = db_name
        self._write_client = write_client
        self._query_client = query_client
        self._writer = None
        self._query_runner = None

    def writer(self, table_name):
        if self._writer is None:
            self._writer = TimestreamTableWriter(
                self.db_name, table_name, self._write_client
            )
        return self._writer

    @cached_property
    def query_runner(self) -> TimeStreamQueryRunner:
        if self._query_runner is None:
            self._query_runner = TimeStreamQueryRunner(self._query_client)
        return self._query_runner

    # Proxy methods for TimestreamTableWriter
    def write_records(self, table_name, records, common_attributes={}):
        return self.writer(table_name).write_records(records, common_attributes)

    def _get_memory_store_retention_hours(self, table_name):
        return self.writer(table_name).get_MemoryStoreRetentionPeriodInHours()

    def _get_magnetic_store_retention_days(self, table_name):
        return self.writer(table_name).get_MagneticStoreRetentionPeriodInDays()

    # todo: in phase 2 - move to BaseMetricStorage
    def get_metrics_table_name_for_resource_type(self, resource_type: str):
        return AWSNaming.TimestreamMetricsTable(None, resource_type)

    def get_earliest_writeable_time_for_resource_type(self, resource_type: str):
        table_name = self.get_metrics_table_name_for_resource_type(
            resource_type=resource_type
        )
        return self.writer(table_name).get_earliest_writeable_time_for_table()

    # Proxy methods for TimeStreamQueryRunner
    def is_table_empty(self, table_name):
        return self.query_runner.is_table_empty(self.db_name, table_name)

    def execute_scalar_query(self, query):
        return self.query_runner.execute_scalar_query(query)

    def execute_scalar_query_date_field(self, query):
        return self.query_runner.execute_scalar_query_date_field(query)

    def execute_query(self, query):
        return self.query_runner.execute_query(query)

    # Added methods from metrics_extractor_utils.py
    def retrieve_last_update_time_for_all_resources(self, logger):
        """
        Retrieve max(time) for each resource_type from {resource_type}_metrics table.

        Args:
            logger (Logger): Logger instance.

        Returns:
            dict: Resource type to last update times, grouped by resource type.
        """
        table_parts = []
        try:
            for resource_type in SettingConfigs.RESOURCE_TYPES:
                timestream_table_name = self.get_metrics_table_name_for_resource_type(
                    resource_type
                )

                if not self.is_table_empty(timestream_table_name):
                    table_parts.append(
                        f"""SELECT \'{resource_type}\' as resource_type, resource_name, max(time) as last_update_time 
                            FROM "{self.db_name}"."{timestream_table_name}" 
                            GROUP BY resource_name"""
                    )
                else:
                    logger.info(
                        f"No data in table {timestream_table_name}, skipping..."
                    )

            if not table_parts:
                return {}

            query = f" UNION ALL ".join(table_parts)
            result = self.execute_query(query)

            # Transform plain result set into grouped data
            transformed_data = {}
            for item in result:
                resource_type = item["resource_type"]
                if resource_type not in transformed_data:
                    transformed_data[resource_type] = []
                transformed_data[resource_type].append(
                    {
                        "resource_name": item["resource_name"],
                        "last_update_time": item["last_update_time"],
                    }
                )
            return transformed_data
        except Exception as e:
            logger.error(e)
            raise MetricsStorageException(f"Error getting last update time: {e}")

    def get_resource_last_update_time_from_json(
        self, last_update_time_json, resource_type, resource_name
    ):
        """
        Get last update time for a specific resource.

        Args:
            last_update_time_json (dict): Last update times grouped by resource type.
            resource_type (str): Resource type.
            resource_name (str): Resource name.

        Returns:
            datetime: Last update time as datetime object, or None if not found.
        """
        if not last_update_time_json:
            return None

        resource_section = last_update_time_json.get(resource_type)
        if not resource_section:
            return None

        for resource_info in resource_section:
            if resource_info["resource_name"] == resource_name:
                return str_utc_datetime_to_datetime(resource_info["last_update_time"])
        return None

    def get_last_update_time_from_metrics_table(
        self, resource_type, resource_name
    ) -> datetime | None:
        metrics_table_name = self.get_metrics_table_name_for_resource_type(
            resource_type
        )

        # check if table is empty
        if self.is_table_empty(metrics_table_name):
            return None

        query = f'SELECT max(time) FROM "{self.db_name}"."{metrics_table_name}" WHERE {self.RESOURCE_NAME_COLUMN_NAME} = \'{resource_name}\''
        last_date = self.execute_scalar_query_date_field(query=query)
        return last_date

    def get_earliest_last_update_time_for_resource_set(
        self, last_update_times, resource_names, resource_type
    ) -> datetime:
        """
        Get the earliest update time for a set of resources.

        Args:
            last_update_times (list): List of last update times for resources.
            resource_names (list): List of resource names.

        Returns:
            datetime: Earliest update time or the earliest writable time if incomplete data.
        """
        if last_update_times:
            resource_dict = {
                item["resource_name"]: item["last_update_time"]
                for item in last_update_times
            }

            if all(resource in resource_dict for resource in resource_names):
                update_times = [
                    str_utc_datetime_to_datetime(resource_dict[resource])
                    for resource in resource_names
                ]
                return min(update_times)

        return self.get_earliest_writeable_time_for_resource_type(
            resource_type=resource_type
        )
