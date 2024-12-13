import pytest
import boto3

from inttest_lib.message_checker import MessagesChecker
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from test_base_class import TestBaseClass


class TestGlueCatalogs(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_DATA_CATALOGS

    @pytest.fixture
    def execution_timestream_metrics_summary(
        self, region, start_epochtimemsec, stack_obj_for_naming
    ):
        """
        Collects summary from relevant timestream table (records only since the test started are included).
        Result is dict: e.g.
              {
               'tables_count': '1',
               'tables_added': '1',
               'partitions_count': '1',
               'partitions_added': '1',
               'indexes_count': '1',
               'indexes_added': '1'
               }
        """
        DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
        TABLE_NAME = AWSNaming.TimestreamMetricsTable(
            stack_obj_for_naming, self.resource_type
        )

        client = boto3.client("timestream-query", region_name=region)
        query_runner = TimeStreamQueryRunner(client)

        query = f"""
                WITH ranked_records AS(
                    SELECT
                        t.*
                        , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS rn_desc
                        , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time ASC) AS rn_asc
                    FROM "{DB_NAME}"."{TABLE_NAME}" t
                    WHERE time > from_milliseconds({start_epochtimemsec})
                ),
                -- filter to retain only the earliest and latest rows for each resource
                min_max_record AS (
                    SELECT *
                    FROM ranked_records
                    WHERE rn_desc = 1 OR rn_asc = 1
                ),
                -- get previous counts for tables, partitions, and indexes
                counts AS (
                    SELECT
                        resource_name,
                        tables_count,
                        LAG(tables_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_tables_count,
                        partitions_count,
                        LAG(partitions_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_partitions_count,
                        indexes_count,
                        LAG(indexes_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_indexes_count,
                        ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS row_num
                    FROM min_max_record
                )
                --final results
                SELECT 
                    tables_count,
                    COALESCE(tables_count - prev_tables_count, 0) AS tables_added,
                    partitions_count,
                    COALESCE(partitions_count - prev_partitions_count, 0) AS partitions_added,
                    indexes_count,
                    COALESCE(indexes_count - prev_indexes_count, 0) AS indexes_added
                FROM counts
                WHERE row_num = 1
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    def test_alerts(self, test_results_messages):
        """
        No Alerts expected for Glue Data Catalogs resource type.
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_error_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :", "FAILED"])
        )
        cnt_all_messages = len(msqchk.subject_contains_all([f"{self.resource_type} :"]))
        assert (
            cnt_error_messages == 0
        ), f"There shouldn't be any {self.resource_type} error message"
        assert (
            cnt_all_messages == 0
        ), f"There shouldn't be any {self.resource_type} message"

    # assert message differs
    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        tables_count = execution_timestream_metrics_summary.get("tables_count", 0)
        tables_added = execution_timestream_metrics_summary.get("tables_added", 0)
        partitions_count = execution_timestream_metrics_summary.get(
            "partitions_count", 0
        )
        partitions_added = execution_timestream_metrics_summary.get(
            "partitions_added", 0
        )
        indexes_count = execution_timestream_metrics_summary.get("indexes_count", 0)
        indexes_added = execution_timestream_metrics_summary.get("indexes_added", 0)

        assert tables_count == "1", "There should be exactly one Glue table."
        assert tables_added == "0", "There shouldn't be any tables deleted."
        assert partitions_count == "0", "There shouldn't be any Glue partition."
        assert partitions_added == "0", "There shouldn't be any partition added."
        assert indexes_count == "0", "There shouldn't be any Glue partition index."
        assert indexes_added == "0", "There shouldn't be any partition index added."

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 0
        ), "There shouldn't be any CloudWatch events"
