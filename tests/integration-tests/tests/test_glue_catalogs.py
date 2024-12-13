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
                SELECT  sum(tables_count) as tables_count, sum(tables_added) as tables_added,
                        sum(partitions_count) as partitions_count, sum(partitions_added) as partitions_added,
                        sum(indexes_count) as indexes_count, sum(indexes_added) as indexes_added
                FROM "{DB_NAME}"."{TABLE_NAME}"
                WHERE time > from_milliseconds({start_epochtimemsec})
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
