from abc import ABC, abstractmethod


class MetricsStorageTypes:
    AWS_TIMESTREAM = "aws_timestream"


class MetricsStorageException(Exception):
    """Exception raised for errors encountered while working metrics storage."""

    pass


class BaseMetricsStorage:
    RESOURCE_NAME_COLUMN_NAME = "resource_name"
