from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from inttest_lib.message_checker import MessagesChecker

from lib.core.constants import SettingConfigResourceTypes
#######################################################################################################################

# so far:
# - skipping tests for metrics (we don't have metrics extractor implemented)

def test_alerts(test_results_messages):
    """
        Checking if correct notifications were sent
    """    
    msqchk = MessagesChecker(test_results_messages)

    cnt_glue_error_messages = len(msqchk.subject_contains_all(["glue_crawlers :", "FAILED"]))
    cnt_glue_all_messages = len(msqchk.subject_contains_all(["glue_crawlers :"]))
    
    assert cnt_glue_error_messages == 1, "There should be exactly one glue crawler error message"
    assert cnt_glue_all_messages == 1, "There should be exactly one glue crawler message"


def test_digest_message(test_results_messages, config_reader, stack_obj_for_naming):
    """
        Checking if digest contains expected information
    """    
    msqchk = MessagesChecker(test_results_messages)

    digest_messages: list[IntegrationTestMessage] = msqchk.subject_contains_all(["Digest Report"])

    message_body = digest_messages[0].MessageBody
    
    # checking if there are mentions of testing stand glue crawlers in the digest
    glue_crawler_names = config_reader.get_names_by_resource_type(SettingConfigResourceTypes.GLUE_CRAWLERS, stack_obj_for_naming)

    assert len(glue_crawler_names) > 0, "There should be glue crawlers in testing scope"

    for glue_crawler_name in glue_crawler_names:
        assert glue_crawler_name in message_body, f"There should be mention of {glue_crawler_name} glue crawler"