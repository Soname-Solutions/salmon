import pytest
import boto3

from lib.core.constants import SettingConfigResourceTypes
from inttest_lib.message_checker import MessagesChecker
from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming

from test_base_class import TestBaseClass


class TestLambdaFunctions(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.LAMBDA_FUNCTIONS

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

        query = f"""SELECT sum(invocation) as invocations, sum(succeeded) as succeeded, sum(failed) as failed
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    # as we got not usual 1 error, but 5 (one for fail-1 Lambda, 2 (considering retries) for fail-2 Lambda, 2 for mix-3 Lambda)
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
            cnt_lambda_error_messages == 5
        ), f"There should be exactly five {self.resource_type} error messages"
        assert (
            cnt_lambda_all_messages == 5
        ), f"There should be exactly five {self.resource_type} messages"

    # assert message differs
    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        invocations = execution_timestream_metrics_summary.get("invocations", 0)
        succeeded = execution_timestream_metrics_summary.get("succeeded", 0)
        failed = execution_timestream_metrics_summary.get("failed", 0)

        assert invocations == "7", "There should be exactly seven Lambda invocations."
        assert succeeded == "2", "There should be two successful Lambda invocations."
        assert failed == "5", "There should be exactly five failed Lambda invocations."

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 7
        ), "There should be seven events, one for each Lambda invocation"

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
