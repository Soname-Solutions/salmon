import pytest
import boto3
import re

from inttest_lib.message_checker import MessagesChecker
from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from test_base_class import TestBaseClass


class TestGlueCatalogs(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_DATA_CATALOGS

    @staticmethod
    def parse_glue_catalog_summary_table(message):
        """Extracts specific parts related to Glue Data Catalogs from the Digest Summary message."""
        result = {}

        # Regex to match the summary table entry for Glue Data Catalogs
        summary_table_glue_catalogs_pattern = re.compile(
            r"\|\s*(it_ts_glue_catalogs)\s*\|\s*Glue Data Catalogs\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*\|\s*(-?\d+)\s*\|"
        )
        # Extract the summary table entry
        summary_table_match = summary_table_glue_catalogs_pattern.search(message)
        if summary_table_match:
            result[summary_table_match.group(1)] = list(
                map(int, summary_table_match.groups()[1:])
            )
        return result

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
                SELECT       
                       tables_count
                     , tables_count - prev_tables_count as tables_added
                     , partitions_count
                     , partitions_count - prev_partitions_count as partitions_added
                     , indexes_count
                     , indexes_count - prev_indexes_count as indexes_added
                FROM (SELECT 
                          tables_count
                        , LAG(tables_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_tables_count
                        , partitions_count
                        , LAG(partitions_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_partitions_count
                        , indexes_count
                        , LAG(indexes_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_indexes_count
                        , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS rn
                      FROM ( 
                          -- Fetch the latest and earliest rows per resource
                            SELECT 
                                  resource_name
                                , time
                                , tables_count
                                , partitions_count                                
                                , indexes_count
                            FROM (
                                SELECT 
                                      resource_name
                                    , time
                                    , partitions_count
                                    , tables_count
                                    , indexes_count 
                                    , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS rn_desc
                                    , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time ASC) AS rn_asc
                                FROM "{DB_NAME}"."{TABLE_NAME}"
                                WHERE time > from_milliseconds({start_epochtimemsec})
                                ) sub1
                            WHERE rn_desc = 1 OR rn_asc = 1
                        ) sub2
                    ) sub3
                WHERE rn =1
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    @pytest.mark.skip(reason="test_alerts is not relevant for TestGlueCatalogs class")
    def test_alerts(self, test_results_messages):
        """
        Checking if correct notifications were sent
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_glue_error_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :", "FAILED"])
        )
        cnt_glue_all_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :"])
        )

        assert (
            cnt_glue_error_messages == 1
        ), f"There should be exactly one {self.resource_type} error message"
        assert (
            cnt_glue_all_messages == 1
        ), f"There should be exactly one {self.resource_type} message"

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
        assert tables_added == "-1", "There should be one table deleted."
        assert partitions_count == "1", "There should be exactly one Glue partition."
        assert partitions_added == "1", "There should be one partition added."
        assert indexes_count == "1", "There should be exactly one Glue partition index."
        assert indexes_added == "1", "There should be one partition index added."

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 2
        ), "There should be 2 events, one for CreatePartition event and the second one for DeleteTable"

        # checking all resources are mentioned
        resource_names_in_events = [
            x["resource_name"] for x in relevant_cloudwatch_events
        ]

        resource_names_in_config = config_reader.get_names_by_resource_type(
            self.resource_type, stack_obj_for_naming
        )
        for resource_name in resource_names_in_config:
            assert (
                resource_name in resource_names_in_events
            ), f"There should be mention of {resource_name} [{self.resource_type}] in CloudWatch alert logs"

    def test_digest_message(
        self, test_results_messages, config_reader, stack_obj_for_naming
    ):
        """
        Checking if digest contains expected information
        """
        msqchk = MessagesChecker(test_results_messages)

        digest_messages: list[IntegrationTestMessage] = msqchk.subject_contains_all(
            ["Digest Report"]
        )

        message_body = digest_messages[0].MessageBody

        # parse and check glue catalog summary table
        self.glue_catalog_summary = self.parse_glue_catalog_summary_table(message_body)

        # checking if there are mentions of testing stand resource in the digest
        resource_names = config_reader.get_names_by_resource_type(
            self.resource_type, stack_obj_for_naming
        )

        assert (
            len(resource_names) > 0
        ), f"There should be {self.resource_type} in testing scope"

        for resource_name in resource_names:
            assert (
                resource_name in message_body
            ), f"There should be mention of {resource_name} [{self.resource_type}]"

        assert "WARNING: Some Glue Data Catalog object(s) deleted." in message_body

        # Tables Added, Partitions Added, Indexes Added, Total Tables, Total Partitions, Total Indexes
        #           -1|                1|             1|            1|                1|            1|
        assert self.glue_catalog_summary["it_ts_glue_catalogs"] == [-1, 1, 1, 1, 1, 1]
