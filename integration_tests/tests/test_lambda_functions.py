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
