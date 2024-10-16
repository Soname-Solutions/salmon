from inttest_lib.message_checker import MessagesChecker


class TestCommon:  # this one doesn't need to be inherited from TestBaseClass (no shared methods)
    def test_digest_received(self, test_results_messages):
        """
        Checking if correct notifications were sent
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_digest_messages = len(msqchk.subject_contains_all(["Digest Report"]))

        assert cnt_digest_messages == 1, "There should be exactly one digest message"

    def test_internal_errors_from_salmon_lambdas(self, test_results_messages):
        """
        internal SALMON lambdas (such as extract-metrics, extract-metrics-orch) are designed to
        send message to internal errors SNS topic upon failure.
        Messages from internal error topic are (as others) collected into target inttest topic.

        For internal error Message markers - there is no subject.
        """
        msqchk = MessagesChecker(test_results_messages)

        cnt_no_subject_messages = len(msqchk.subject_contains_all(["No subject"]))

        assert (
            cnt_no_subject_messages == 0
        ), "There shouldn't be any internal error messages"
