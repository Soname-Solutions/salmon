import pytest
import boto3

from lib.core.constants import SettingConfigResourceTypes
from inttest_lib.message_checker import MessagesChecker
from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming

from test_base_class import TestBaseClass


class TestLambdaFunctions(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.LAMBDA_FUNCTIONS

    # additional field to check - actions failed
    @pytest.fixture
    def execution_timestream_metrics_summary(
        self, region, start_epochtimemsec, stack_obj_for_naming
    ):
        """
        Collects summary from relevant timestream table (records only since the test started are included).
        Result is dict: e.g. {'executions': '2', 'succeeded': '1', 'failed': '1'}
        """
        DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
        TABLE_NAME = AWSNaming.TimestreamMetricsTable(
            stack_obj_for_naming, self.resource_type
        )

        client = boto3.client("timestream-query", region_name=region)
        query_runner = TimeStreamQueryRunner(client)

        query = f"""SELECT sum(attempt) as executions, sum(succeeded) as succeeded, sum(failed) as failed
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    # as we got not usual 1 error, but 3 (one for fail-1 Lambda, and 2 (considering retries) for fail-2 Lambda)
    def test_alerts(self, test_results_messages):
        """
        Checking if correct notifications were sent
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_lambda_error_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :", "FAILED"])
        )
        cnt_lambda_all_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :"])
        )

        assert (
            cnt_lambda_error_messages == 3
        ), f"There should be exactly three {self.resource_type} error messages"
        assert (
            cnt_lambda_all_messages == 3
        ), f"There should be exactly three {self.resource_type} messages"

    # assert message differs
    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        executions = execution_timestream_metrics_summary.get("executions", 0)
        succeeded = execution_timestream_metrics_summary.get("succeeded", 0)
        failed = execution_timestream_metrics_summary.get("failed", 0)

        assert (
            executions == "4"
        ), "There should be exactly four executions (considering retry attempts)."
        assert succeeded == "1", "There should be exactly 1 successful execution."
        assert (
            failed == "3"
        ), "There should be exactly 3 failed executions (considering retry attempts)."

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 4
        ), "There should be 4 events, one for each Lambda attempt"

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