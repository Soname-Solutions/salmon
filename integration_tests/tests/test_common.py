from inttest_lib.message_checker import MessagesChecker

def test_digest_received(test_results_messages):
    """
        Checking if correct notifications were sent
    """    
    msqchk = MessagesChecker(test_results_messages)

    cnt_digest_messages = len(msqchk.subject_contains_all(["Digest Report"]))
    
    assert cnt_digest_messages == 1, "There should be exactly one digest message"

def test_internal_errors_from_async_lambdas(test_results_messages):
    """
        Most of the SALMON lambdas (such as extract-metrics, extract-metrics-orch) run in async
        mode, so failure notifications are sent via Lambda destination.
        Message markers - there is no subject.
        For SALMON lambda(s) running in sync mode (e.g. notifications) - see the next test
    """    
    msqchk = MessagesChecker(test_results_messages)

    cnt_no_subject_messages = len(msqchk.subject_contains_all(["No subject"]))
    
    assert cnt_no_subject_messages == 0, "There shouldn't be any internal error messages"

