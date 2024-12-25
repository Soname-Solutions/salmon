import boto3
from abc import ABC, abstractmethod
from datetime import datetime

from lib.aws import Boto3ClientCreator, TimestreamTableWriter, TimeStreamQueryRunner


class MetricsExtractorException(Exception):
    """Exception raised for errors encountered while processing metrics extraction."""

    pass


class BaseMetricsExtractor(ABC):
    """
    Base Class which provides unified functionality for extracting metrics

    Attributes:
        boto3_client_creator: client creator (Boto3ClientCreator object).
        aws_client_name: Boto3 AWS Service client name.
        resource_name (str): Name of the resource (e.g. Glue job, Lambda Function etc.) we are extracting metrics for
        monitored_environment_name (str): Name of the monitored environment
        timestream_db_name (str): Name of the Timestream DB (where metrics are written to)
        timestream_metrics_table_name (str): Name of the Timestream table (where metrics are written to)
    """

    RESOURCE_NAME_COLUMN_NAME = "resource_name"
    EXECUTION_MEASURE_NAME = "execution"
    COUNT_MEASURE_NAME = "count"
    ERROR_MEASURE_NAME = "error"

    def __init__(
        self,
        boto3_client_creator: Boto3ClientCreator,
        aws_client_name: str,
        resource_name: str,
        monitored_environment_name: str,
    ):
        self.boto3_client_creator = boto3_client_creator
        self.aws_client_name = aws_client_name
        self.resource_name = resource_name
        self.monitored_environment_name = monitored_environment_name

    def get_aws_service_client(self, aws_client_name: str | None = None):
        """
        Returns boto3 client for input aws_client_name if provided,
        else creates for aws_client_name defined in metrics_extractor object.
        """
        return self.boto3_client_creator.get_client(
            aws_client_name if aws_client_name else self.aws_client_name
        )

    @abstractmethod
    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):  # type: ignore
        """
        Extract metrics data from AWS and convert them to Timestream records.
        Returns:
            records (list): List of Timestream records
            common_attributes (dict): Common attributes for all records (e.g. dimensions)
        """
        pass

    def write_metrics(
        self, records, common_attributes, timestream_table_writer: TimestreamTableWriter
    ):
        timestream_table_writer.write_records(records, common_attributes)
