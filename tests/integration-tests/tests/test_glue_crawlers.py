from lib.core.constants import SettingConfigResourceTypes
from inttest_lib.message_checker import MessagesChecker
from test_base_class import TestBaseClass


class TestGlueCrawlers(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_CRAWLERS

    # differs from default behavior: "Failed" in not in uppercase in message
    def test_alerts(self, test_results_messages):
        """
        Checking if correct notifications were sent
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_glue_error_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :", "Failed"])
        )
        cnt_glue_all_messages = len(
            msqchk.subject_contains_all([f"{self.resource_type} :"])
        )

        assert (
            cnt_glue_error_messages == 1
        ), f"There should be exactly one of {self.resource_type} error message"
        assert (
            cnt_glue_all_messages == 1
        ), f"There should be exactly one {self.resource_type} message"
