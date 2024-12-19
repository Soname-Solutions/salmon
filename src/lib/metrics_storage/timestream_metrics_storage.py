from functools import cached_property
import boto3
from lib.aws.timestream_manager import TimestreamTableWriter, TimeStreamQueryRunner


class TimestreamMetricsStorage:
    """
    A proxy class for TimestreamTableWriter and TimeStreamQueryRunner to provide a unified interface for interacting
    with Timestream metrics storage. Clients and writer are lazily initialized to optimize for partial use cases.
    """

    def __init__(
        self, db_name: str, table_name: str, write_client=None, query_client=None
    ):
        """
        Initialize the TimestreamMetricsStorage.

        Args:
            db_name (str): Name of the Timestream database.
            table_name (str): Name of the Timestream table.
            write_client: Optional boto3 Timestream write client. Lazily initialized if not provided.
            query_client: Optional boto3 Timestream query client. Lazily initialized if not provided.
        """
        self.db_name = db_name
        self.table_name = table_name
        self._write_client = write_client
        self._query_client = query_client
        self._writer = None

    @cached_property
    def write_client(self):
        """
        Lazily initializes the Timestream write client.
        """
        if self._write_client is None:
            self._write_client = boto3.client("timestream-write")
        return self._write_client

    @cached_property
    def query_client(self):
        """
        Lazily initializes the Timestream query client.
        """
        if self._query_client is None:
            self._query_client = boto3.client("timestream-query")
        return self._query_client

    @cached_property
    def writer(self):
        """
        Lazily initializes the TimestreamTableWriter.
        """
        if self._writer is None:
            self._writer = TimestreamTableWriter(
                self.db_name, self.table_name, self.write_client
            )
        return self._writer

    # Proxy methods for TimestreamTableWriter
    def write_records(self, records, common_attributes={}):
        """
        Write records to the Timestream database.

        Args:
            records (list): List of records to write.
            common_attributes (dict): Common attributes for the records.
        """
        return self.writer.write_records(records, common_attributes)

    def get_memory_store_retention_hours(self):
        """
        Get the memory store retention period in hours.

        Returns:
            int: Retention period in hours.
        """
        return self.writer.get_MemoryStoreRetentionPeriodInHours()

    def get_magnetic_store_retention_days(self):
        """
        Get the magnetic store retention period in days.

        Returns:
            int: Retention period in days.
        """
        return self.writer.get_MagneticStoreRetentionPeriodInDays()

    def get_earliest_writeable_time(self):
        """
        Get the earliest writeable time for the table based on retention policies.

        Returns:
            datetime: Earliest writeable time.
        """
        return self.writer.get_earliest_writeable_time_for_table()

    # Proxy methods for TimeStreamQueryRunner
    def is_table_empty(self):
        """
        Check if the table is empty.

        Returns:
            bool: True if the table is empty, False otherwise.
        """
        return TimeStreamQueryRunner(self.query_client).is_table_empty(
            self.db_name, self.table_name
        )

    def execute_scalar_query(self, query):
        """
        Execute a scalar query and return the result.

        Args:
            query (str): The query to execute.

        Returns:
            str: Query result.
        """
        return TimeStreamQueryRunner(self.query_client).execute_scalar_query(query)

    def execute_scalar_query_date(self, query):
        """
        Execute a scalar query expecting a datetime result.

        Args:
            query (str): The query to execute.

        Returns:
            datetime: Query result as datetime.
        """
        return TimeStreamQueryRunner(self.query_client).execute_scalar_query_date_field(
            query
        )

    def execute_query(self, query):
        """
        Execute a general query and return the results.

        Args:
            query (str): The query to execute.

        Returns:
            list[dict]: List of result rows as dictionaries.
        """
        return TimeStreamQueryRunner(self.query_client).execute_query(query)
