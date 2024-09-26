from lib.core.constants import SettingConfigResourceTypes
from lib.aws.glue_manager import GlueManager
from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from inttest_lib.message_checker import MessagesChecker

from test_base_class import TestBaseClass


class TestGlueDQ(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_DATA_QUALITY

    # as we got not usual 1 error, but 2 (for independent DQ and GlueJob DQ)
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

        # 1 - alert for ruleset inside Glue Job, 1 - for independent ruleset
        assert (
            cnt_glue_error_messages == 2
        ), f"There should be exactly two {self.resource_type} error messages"
        assert (
            cnt_glue_all_messages == 2
        ), f"There should be exactly two {self.resource_type} messages"

    # assert message differs
    def test_timestream_records(self, execution_timestream_metrics_summary):
        """
        Checking if timestream table is populated with correct data
        """
        executions = execution_timestream_metrics_summary.get("executions", 0)
        succeeded = execution_timestream_metrics_summary.get("succeeded", 0)
        failed = execution_timestream_metrics_summary.get("failed", 0)

        assert (
            executions == "2"
        ), "There should be exactly 2 executions. One for each INDEPENDENT glue dq ruleset."
        assert succeeded == "1", "There should be exactly 1 successful execution."
        assert failed == "1", "There should be exactly 1 failed execution."

    # here we extract rulesetnames differently - config_reader.get_glue_dq_names
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

        # checking if there are mentions of testing stand glue jobs in the digest
        glue_ruleset_names, _ = config_reader.get_glue_dq_names(
            GlueManager.DQ_Catalog_Context_Type, stack_obj_for_naming
        )

        assert (
            len(glue_ruleset_names) > 0
        ), "There should be glue rulesets in testing scope"

        for glue_ruleset_name in glue_ruleset_names:
            assert (
                glue_ruleset_name in message_body
            ), f"There should be mention of {glue_ruleset_name} glue ruleset"
