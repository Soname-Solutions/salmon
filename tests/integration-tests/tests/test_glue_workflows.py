import pytest
import boto3

from lib.core.constants import SettingConfigResourceTypes
from lib.aws.aws_naming import AWSNaming
from lib.aws.timestream_manager import TimeStreamQueryRunner

from test_base_class import TestBaseClass


class TestGlueWorkflows(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_WORKFLOWS

    # additional field to check - actions failed
    @pytest.fixture
    def execution_timestream_metrics_summary(
        self, region, start_epochtimemsec, stack_obj_for_naming
    ):
        """
        Collects summary from relevant timestream table (records only since the test started are included).
        Result is dict: e.g. {'executions': '2', 'succeeded': '1', 'failed': '1', 'actions_failed': '1'}
        """
        DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
        TABLE_NAME = AWSNaming.TimestreamMetricsTable(
            stack_obj_for_naming, SettingConfigResourceTypes.GLUE_WORKFLOWS
        )

        client = boto3.client("timestream-query", region_name=region)
        query_runner = TimeStreamQueryRunner(client)

        query = f"""SELECT sum(execution) as executions, sum(succeeded) as succeeded, sum(failed) as failed
                        , sum(actions_failed) as actions_failed
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        return result[
            0
        ]  # returning the first record (it's only 1 record in resultset by query design)

    # additional field to check - actions failed
    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        executions = execution_timestream_metrics_summary.get("executions", 0)
        succeeded = execution_timestream_metrics_summary.get("succeeded", 0)
        failed = execution_timestream_metrics_summary.get("failed", 0)
        actions_failed = execution_timestream_metrics_summary.get("actions_failed", 0)

        assert (
            executions == "2"
        ), "There should be exactly 2 executions. One for each glue workflow."
        assert succeeded == "1", "There should be exactly 1 successful execution."
        assert failed == "1", "There should be exactly 1 failed execution."
        assert actions_failed == "1", "There should be exactly 1 failed action."
