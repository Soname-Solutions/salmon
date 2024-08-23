from inttest_lib.message_checker import MessagesChecker

def test_digest_received(test_results_messages):
    """
        Checking if correct notifications were sent
    """    
    msqchk = MessagesChecker(test_results_messages)

    cnt_digest_messages = len(msqchk.subject_contains_all(["Digest Report"]))
    
    assert cnt_digest_messages == 1, "There should be exactly one digest message"

