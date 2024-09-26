import pytest
import boto3

from lib.core.constants import SettingConfigResourceTypes
from inttest_lib.message_checker import MessagesChecker

from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming

from test_base_class import TestBaseClass


@pytest.mark.skip
class TestLambdaFunctions(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.LAMBDA_FUNCTIONS

    # so far, here we have only executions count
    @pytest.fixture
    def execution_timestream_metrics_summary(
        self, region, start_epochtimemsec, stack_obj_for_naming
    ):
        """
        Collects count of lambda executions
        Result is dict: e.g. {'executions': '2'}
        """
        DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
        TABLE_NAME = AWSNaming.TimestreamMetricsTable(
            stack_obj_for_naming, SettingConfigResourceTypes.LAMBDA_FUNCTIONS
        )

        client = boto3.client("timestream-query", region_name=region)
        query_runner = TimeStreamQueryRunner(client)

        query = f"""SELECT count(*) as executions
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE measure_name = 'execution' AND time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    @pytest.fixture
    def error_timestream_metrics_summary(
        self, region, start_epochtimemsec, stack_obj_for_naming
    ):
        """
        Collects count of lambda errors
        Result is dict: e.g. {'errors': '2'}
        """
        DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
        TABLE_NAME = AWSNaming.TimestreamMetricsTable(
            stack_obj_for_naming, SettingConfigResourceTypes.LAMBDA_FUNCTIONS
        )

        client = boto3.client("timestream-query", region_name=region)
        query_runner = TimeStreamQueryRunner(client)

        query = f"""SELECT count(*) as errors
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE measure_name = 'error' AND time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    def test_timestream_records(
        self, execution_timestream_metrics_summary, error_timestream_metrics_summary
    ):
        """
        Checking if timestream table is populated with correct data
        """
        executions = execution_timestream_metrics_summary.get("executions", 0)
        errors = error_timestream_metrics_summary.get("errors", 0)

        assert (
            executions == "2"
        ), "There should be exactly 2 executions. One for each lambda function."
        assert errors == "1", "There should be exactly 1 failed execution."
