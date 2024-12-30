from abc import ABC, abstractmethod


class MetricsStorageException(Exception):
    """Exception raised for errors encountered while working metrics storage."""

    pass


class BaseMetricsStorage:
    RESOURCE_NAME_COLUMN_NAME = "resource_name"

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
