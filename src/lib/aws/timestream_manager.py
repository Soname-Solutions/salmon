import boto3

from datetime import datetime
import time


def iso_time_to_epoch_milliseconds(iso_date: str) -> str:
    """
    Convert an ISO 8601 formatted date string to the number of milliseconds since the Unix epoch.
    If the input is None, the current time in milliseconds since the Unix epoch is returned.

    Parameters:
    iso_date (str): An ISO 8601 formatted date string (e.g., "2023-11-21T21:39:09Z").
                    If None, the current time is used.

    Returns:
    str: The number of milliseconds since the Unix epoch as a string.
    """

    # If the input is None, use the current time
    if iso_date is None:
        epoch_time = time.time()
    else:
        # Convert the ISO date string to a datetime object
        dt = datetime.fromisoformat(iso_date.rstrip("Z"))
        # Convert the datetime object to epoch time in seconds
        epoch_time = dt.timestamp()

    # Convert epoch time to milliseconds and return as string
    return str(int(epoch_time * 1000))


class TimestreamTableWriter:
    """
    This class provides an interface to write records to a specified Amazon Timestream table.
    It uses the AWS SDK for Python (Boto3) to interact with the
    Timestream service.

    Attributes:
        db_name (str): The name of the Timestream database.
        table_name (str): The name of the Timestream table.
        timestream_write_client: The Boto3 Timestream write client. If not provided,
            a new client instance is created.

    Methods:
        write_records(records): Writes a list of records to the Timestream table.
    """

    def __init__(self, db_name: str, table_name: str, timestream_write_client=None):
        """
        Initializes a new TimestreamTableWriter instance.

        Args:
            db_name (str): The name of the Timestream database.
            table_name (str): The name of the Timestream table.
            timestream_write_client: An optional Boto3 Timestream write client.
                If none is provided, a new client instance will be created.
        """        
        self.db_name = db_name
        self.table_name = table_name
        self.timestream_write_client = (
            boto3.client("timestream-write")
            if timestream_write_client is None
            else timestream_write_client
        )

    def write_records(self, records):
        """
        Writes a list of records to the Timestream table.

        Args:
            records: A list of records to be written to the Timestream table.

        Returns:
            The response from the Timestream write_records API call.

        Todo:
            Introduce records buffering to support batches of less than 100 records.
        """                
        result = self.timestream_write_client.write_records(
            DatabaseName=self.db_name, TableName=self.table_name, Records=records
        )
        # todo: later need to introduce records buffering (batches < 100 records)
        return result
        
