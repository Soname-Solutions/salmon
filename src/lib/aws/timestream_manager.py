import boto3

from datetime import datetime, timedelta
import time
import dateutil.tz


class TimestreamTableWriterException(Exception):
    """Exception raised for errors encountered while interacting with TimeStream DB."""
    pass

class TimestreamQueryException(Exception):
    """Exception raised for errors encountered while interacting with TimeStream DB."""
    pass

class TimestreamTableWriter:
    """
    This class provides an interface to write records to a specified Amazon Timestream table as well as some helper methods.
    It uses the AWS SDK for Python (Boto3) to interact with the Timestream service.

    Attributes:
        db_name (str): The name of the Timestream database.
        table_name (str): The name of the Timestream table.
        timestream_write_client: The Boto3 Timestream write client. If not provided,
            a new client instance is created.

    Methods:
        write_records(records): Writes a list of records to the Timestream table.
    """

    RECORDS_BATCH_SIZE = (
        100  # Maximum number of records inserted per one write (AWS Limit)
    )

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

    @staticmethod
    def print_rejected_records_exceptions(err):
        """
        Prints detailed information about rejected records exceptions.

        This method is useful for debugging when the Timestream write client rejects records.

        Args:
            err: The exception object received from the Timestream write client which contains
                 details about the rejected records.

        Returns:
            None
        """        
        print("RejectedRecords: ", err)
        for rr in err.response["RejectedRecords"]:
            print("Rejected Index " + str(rr["RecordIndex"]) + ": " + rr["Reason"])
            if "ExistingVersion" in rr:
                print("Rejected record existing version: ", rr["ExistingVersion"])

    @staticmethod
    def epoch_milliseconds_str(epoch_seconds: float = None) -> str:
        """
        Converts epoch time in seconds to a string representation in milliseconds.

        If no argument is provided, the current time is used. 

        Args:
            epoch_seconds (float, optional): The epoch time in seconds. If None,
                                             the current time is used. Defaults to None.

        Returns:
            str: The epoch time in milliseconds as a string.
        """        
        tmp = epoch_seconds if epoch_seconds is not None else time.time()
        return str(int(round(tmp * 1000)))
    
    @staticmethod
    def datetime_to_epoch_milliseconds(datetime_value: datetime) -> str:
        """
            Convert a datetime object to a string representation in milliseconds (which is required to timestream record)

            Parameters:
            datetime_value (datetime): The datetime object to be converted.

            Returns:
            str: The datetime object as a string in milliseconds.        
        """        
        return TimestreamTableWriter.epoch_milliseconds_str(datetime_value.timestamp())

    @staticmethod
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
            return TimestreamTableWriter.epoch_milliseconds_str()
        else:
            # Convert the ISO date string to a datetime object
            dt = datetime.fromisoformat(iso_date.rstrip("Z"))
            # Convert the datetime object to epoch time in seconds
            epoch_time = dt.timestamp()
            return TimestreamTableWriter.epoch_milliseconds_str(epoch_time)

    def _write_batch(self, records, common_attributes={}):
        """
        Writes a single batch (up to 100 records) to the Timestream table.

        Args:
            records: A list of records to be written to the Timestream table.

        Returns:
            The response from the Timestream write_records API call.

        Todo:
            Introduce records buffering to support batches of less than 100 records.
        """
        try:
            result = self.timestream_write_client.write_records(
                DatabaseName=self.db_name,
                TableName=self.table_name,
                Records=records,
                CommonAttributes=common_attributes,
            )
            print(
                "WriteRecords Status: [%s]"
                % result["ResponseMetadata"]["HTTPStatusCode"]
            )
            return result
        except self.timestream_write_client.exceptions.RejectedRecordsException as err:
            error_message = (
                f"Records were rejected for {self.db_name}.{self.table_name}: {err}."
            )
            self.print_rejected_records_exceptions(err)
            raise (TimestreamTableWriterException(error_message))
        except Exception as err:
            error_message = (
                f"Error writing records into {self.db_name}.{self.table_name}: {err}."
            )
            raise (TimestreamTableWriterException(error_message))

    def write_records(self, records, common_attributes={}):
        """
        Orchestrates the process of writing records to the Timestream table in batches of 100.

        Args:
            records: A list of records to be written to the Timestream table.

        Returns:
            A list of responses from the Timestream write_records API call for each batch.
        """
        responses = []

        for i in range(0, len(records), self.RECORDS_BATCH_SIZE):
            batch = records[i : i + self.RECORDS_BATCH_SIZE]
            response = self._write_batch(batch, common_attributes)
            responses.append(response)

        return responses

    def _get_table_props(self):
        """
        Retrieves the properties of the specified Timestream table. For internal use.

        Returns:
            dict: A dictionary containing the properties of the table.
        """        
        try:
            result = self.timestream_write_client.describe_table(
                DatabaseName=self.db_name, TableName=self.table_name
            )
            return result
        except Exception as err:
            error_message = (
                f"Error getting table info for {self.db_name}.{self.table_name}: {err}."
            )
            raise (TimestreamTableWriterException(error_message))

    def get_MemoryStoreRetentionPeriodInHours(self):
        """
        Gets the Memory Store retention period in hours for the Timestream table.

        Returns:
            int: The retention period of the Memory Store in hours.
        """        
        table_props = self._get_table_props()

        try:
            value = (
                table_props.get("Table")
                .get("RetentionProperties")
                .get("MemoryStoreRetentionPeriodInHours")
            )
            return int(value)
        except Exception as err:
            error_message = f"Error getting MemoryStoreRetentionPeriodInHours for {self.db_name}.{self.table_name}: {err}."
            raise (TimestreamTableWriterException(error_message))

    def get_MagneticStoreRetentionPeriodInDays(self):
        """
        Gets the Magnetic Store retention period in days for the Timestream table.

        Returns:
            int: The retention period of the Magnetic Store in days.
        """

        table_props = self._get_table_props()

        try:
            value = (
                table_props.get("Table")
                .get("RetentionProperties")
                .get("MagneticStoreRetentionPeriodInDays")
            )
            return int(value)
        except Exception as err:
            error_message = f"Error getting MagneticStoreRetentionPeriodInDays for {self.db_name}.{self.table_name}: {err}."
            raise (TimestreamTableWriterException(error_message))


    def get_earliest_writeable_time_for_table(self):
        utc_tz = dateutil.tz.gettz('UTC')
        return datetime.now(tz=utc_tz) - timedelta(hours=self.get_MemoryStoreRetentionPeriodInHours())

class TimeStreamQueryRunner:
    def __init__(self, timestream_query_client):
        self.timestream_query_client = timestream_query_client

    def execute_scalar_query(self, query):
        """
        Executes a scalar query (result = one row, one column) and returns the result.

        Args:
            query (str): The query to be executed.

        Returns:
            str: The result of the query.            
        """
        try:
            response = self.timestream_query_client.query(QueryString=query)
            first_record_data = response["Rows"][0]["Data"]
            first_field_data = first_record_data[0]
            if "ScalarValue" in first_field_data:
                return first_field_data["ScalarValue"]
            else:
                return None
        except Exception as e:
            error_message = f"Error running query: {e}"
            raise (TimestreamQueryException(error_message))
        
    def execute_scalar_query_date_field(self, query):
        """
        Executes a scalar query specifically for date results field (result = one row, one column) 
        and returns the result as a datetime object.

        Args:
            query (str): The query to be executed.

        Returns:
            datetime: The result of the query as a datetime object.            
        """
        result_str = self.execute_scalar_query(query)        

        if result_str is None:
            return None

        try:
            result_datetime = datetime.strptime(result_str.rstrip("0"), "%Y-%m-%d %H:%M:%S.%f")
            utc_tz = dateutil.tz.gettz('UTC')
            result_datetime = result_datetime.replace(tzinfo=utc_tz)
            return result_datetime
        except Exception as e:
            error_message = f"Error converting result to datetime: {e}"
            raise TimestreamQueryException(error_message)
 