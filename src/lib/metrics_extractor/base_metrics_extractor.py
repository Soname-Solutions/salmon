from abc import ABC, abstractmethod
from datetime import datetime

from lib.aws.timestream_manager import TimestreamTableWriter

class BaseMetricsExtractor(ABC):
    """
    Base Class which provides unified functionality for extracting metrics

    Attributes:
        aws_service_client: Boto3 AWS Service client
        entity_name (str): Name of the entity (e.g. Glue job) we are extracting metrics for        
        monitored_environment_name (str): Name of the monitored environment
        timestream_db_name (str): Name of the Timestream DB (where metrics are written to)
        timestream_metrics_table_name (str): Name of the Timestream table (where metrics are written to)                
    """ 


    def __init__(
        self, aws_service_client, entity_name, monitored_environment_name, timestream_db_name, timestream_metrics_table_name
    ):
        self.aws_service_client = aws_service_client
        self.entity_name = entity_name
        self.monitored_environment_name = monitored_environment_name
        self.timestream_db_name = timestream_db_name
        self.timestream_metrics_table_name = timestream_metrics_table_name

    @abstractmethod
    def get_last_update_time(self, timestream_query_client) -> datetime:
        """
        Get time of this entity's data latest update (we append data since that time only)
        """
        pass

    @abstractmethod
    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):
        """
        Extract metrics data from AWS and convert them to Timestream records.
        Returns:
            records (list): List of Timestream records
            common_attributes (dict): Common attributes for all records (e.g. dimensions)
        """
        pass
        

    def write_metrics(self, records, common_attributes, timestream_table_writer: TimestreamTableWriter):        
        timestream_table_writer.write_records(records, common_attributes)

