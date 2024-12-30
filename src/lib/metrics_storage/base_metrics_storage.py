from abc import ABC, abstractmethod


class MetricsStorageException(Exception):
    """Exception raised for errors encountered while working metrics storage."""

    pass


class BaseMetricsStorage:
    RESOURCE_NAME_COLUMN_NAME = "resource_name"

    def __init__(self, db_name: str):
        """
        Initialize the MetricsStorage.

        Args:
            db_name (str): Name of the target database.
        """
        self.db_name = db_name

    @abstractmethod
    def retrieve_last_update_time_for_all_resources(self, logger):
        """
        Retrieve max(time) for each resource_type from {resource_type}_metrics table.

        Args:
            logger (Logger): Logger instance.

        Returns:
            dict: Resource type to last update times, grouped by resource type.
        """
        pass

    @abstractmethod
    def is_table_empty(self, table_name) -> bool:
        pass

    @abstractmethod
    def write_records(self, table_name, records, common_attributes={}) -> list:
        """
        Writes records to the storage (into a table specific for a resource type)

        Args:
            table_name: target table name
            records: list of records (in timeseries like format: time, dimensions list, metrics ...)
            common_attributes: a list of attributes applied to all records (e.g. dimensions)
        """
        pass
