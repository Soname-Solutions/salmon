import pytest
import boto3

from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from inttest_lib.message_checker import MessagesChecker

from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.aws_naming import AWSNaming


class TestBaseClass:
    """ """

    __test__ = False  # Pytest should avoid running tests in this Base class

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("Subclasses must implement set_resource_type method")
        # 1. set resource_type
        # 2. set detail-type for CloudWatch alerts event entry, e.g.:
        # cls.resource_type = SettingConfigResourceTypes.GLUE_JOBS
        # cls.cloudwatch_detail_type = "Glue Job State Change"

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

        query = f"""SELECT sum(execution) as executions, sum(succeeded) as succeeded, sum(failed) as failed
                    FROM "{DB_NAME}"."{TABLE_NAME}"
                    WHERE time > from_milliseconds({start_epochtimemsec})
        """
        result = query_runner.execute_query(query=query)

        # returning the first record (it's only 1 record in resultset by query design)
        return result[0]

    @pytest.fixture
    def relevant_cloudwatch_events(self, cloudwatch_alerts_events) -> list[dict]:
        return [
            x
            for x in cloudwatch_alerts_events
            if x["resource_type"] == self.resource_type
        ]

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

    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        executions = execution_timestream_metrics_summary.get("executions", 0)
        succeeded = execution_timestream_metrics_summary.get("succeeded", 0)
        failed = execution_timestream_metrics_summary.get("failed", 0)

        assert (
            executions == "2"
        ), f"There should be exactly 2 executions. One for each of {self.resource_type}."
        assert succeeded == "1", "There should be exactly 1 successful execution."
        assert failed == "1", "There should be exactly 1 failed execution."

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

    def test_cloudwatch_alert_events(
        self, relevant_cloudwatch_events, config_reader, stack_obj_for_naming
    ):
        # checking events count
        assert (
            len(relevant_cloudwatch_events) == 2
        ), "There should be 2 events, one for each execution"

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
