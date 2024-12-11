import pytest
import boto3

from lib.core.constants import SettingConfigResourceTypes
from inttest_lib.message_checker import MessagesChecker
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming

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
        assert tables_added == "0", "There shouldn't be any table added."
        assert partitions_count == "1", "There should be exactly one Glue partition."
        assert partitions_added == "1", "There should be one partition added."
        assert indexes_count == "1", "There should be exactly one Glue partition index."
        assert indexes_added == "1", "There should be one partition index added."

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 7
        ), "There should be 6 events, one for each Lambda invocation"

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
