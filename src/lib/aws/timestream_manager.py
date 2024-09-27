import boto3

from datetime import datetime, timedelta, timezone
import dateutil
from functools import cached_property

from pydantic import BaseModel
from typing import List, Optional

#################################################


class TimestreamTableWriterException(Exception):
    """Exception raised for errors encountered while interacting with TimeStream DB."""

    pass


class TimestreamQueryException(Exception):
    """Exception raised for errors encountered while interacting with TimeStream DB."""

    pass


#################################################
# Query Response Pydantic classes


class ScalarType(BaseModel):
    ScalarValue: Optional[str]


class Data(BaseModel):
    Data: List[ScalarType]


class ColumnType(BaseModel):
    ScalarType: str


class ColumnInfo(BaseModel):
    Name: str
    Type: ColumnType


class QueryStatus(BaseModel):
    ProgressPercentage: float
    CumulativeBytesScanned: int
    CumulativeBytesMetered: int


class ResponseMetadata(BaseModel):
    RequestId: str
    HTTPStatusCode: int
    RetryAttempts: int


class QueryResponse(BaseModel):
    QueryId: str
    Rows: List[Data]
    ColumnInfo: List[ColumnInfo]
    QueryStatus: QueryStatus
    ResponseMetadata: ResponseMetadata


#################################################


def convert_timestream_datetime_str(datetime_str: str) -> datetime:
    """
    Parses and converts datetime string extracted from Timestream DB, adds UTC timezone.
    In timestream it is stored as "2024-09-20 16:39:05.000000000" (tz-naive), but by design it's UTC time
    """
    try:
        if "." in datetime_str:
            date_part, fractional_part = datetime_str.split(".")
            fractional_part = fractional_part.ljust(6, "0")[:6]
            s_adjusted = f"{date_part}.{fractional_part}"
            dt = datetime.strptime(s_adjusted, "%Y-%m-%d %H:%M:%S.%f")
        else:
            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except Exception as e:
        error_message = f"Error converting result to datetime: {e}"
        raise TimestreamQueryException(error_message)


#################################################


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

    @cached_property
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
        utc_tz = dateutil.tz.gettz("UTC")
        return datetime.now(tz=utc_tz) - timedelta(
            hours=self.get_MemoryStoreRetentionPeriodInHours()
        )


class TimeStreamQueryRunner:
    def __init__(self, timestream_query_client):
        self.timestream_query_client = timestream_query_client

    def is_table_empty(self, database_name, table_name):
        """
        Checks if the specified table is empty.

        Args:
            database_name (str): The name of the database.
            table_name (str): The name of the table.

        Returns:
            bool: True if the table is empty, False otherwise.
        """
        try:
            query = f'SHOW MEASURES FROM "{database_name}"."{table_name}"'
            response = self.timestream_query_client.query(QueryString=query)

            return response["Rows"] == []
        except Exception as e:
            error_message = f"Error checking table is empty: {e}"
            raise (TimestreamQueryException(error_message))

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
        else:
            return convert_timestream_datetime_str(result_str)

    def execute_query(self, query):
        """
        Executes a query and returns the result.

        Args:
            query (str): The query to be executed.

        Returns:
            str: The result of the query.
        """
        try:
            response = self.timestream_query_client.query(QueryString=query)
            result = QueryResponse(**response)

            column_names = [x.Name for x in result.ColumnInfo]

            result_rows = []
            for row in result.Rows:
                values = [x.ScalarValue for x in row.Data]
                data_row = dict(zip(column_names, values))
                result_rows.append(data_row)

            return result_rows
        except Exception as e:
            error_message = f"Error running query: {e}"
            raise (TimestreamQueryException(error_message))
