
from inttest_lib.message_checker import MessagesChecker


def test_sqs_messages(sqs_messages):
    msqchk = MessagesChecker(sqs_messages)

    cnt_glue_error_messages = len(msqchk.subject_contains_all(["glue_jobs :", "FAILED"]))
    cnt_glue_all_messages = len(msqchk.subject_contains_all(["glue_jobs :"]))
    
    assert cnt_glue_error_messages == 1, "There should be exactly one glue job error message"
    assert cnt_glue_all_messages == 1, "There should be exactly one glue job message"
