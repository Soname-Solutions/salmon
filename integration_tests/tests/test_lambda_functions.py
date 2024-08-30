import pytest
import boto3
from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from inttest_lib.message_checker import MessagesChecker

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from lib.aws.timestream_manager import TimeStreamQueryRunner

@pytest.fixture(scope='session')
def lambda_execution_timestream_metrics_summary(region, start_epochtimemsec, stack_obj_for_naming):
    """
        Collects count of lambda executions
        Result is dict: e.g. {'executions': '2'}
    """
    DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
    TABLE_NAME = AWSNaming.TimestreamMetricsTable(
        stack_obj_for_naming, SettingConfigResourceTypes.LAMBDA_FUNCTIONS
    )

    client = boto3.client("timestream-query", region_name=region)
    query_runner = TimeStreamQueryRunner(client)

    query = f"""SELECT count(*) as executions
                FROM "{DB_NAME}"."{TABLE_NAME}"
                WHERE measure_name = 'execution' AND time > from_milliseconds({start_epochtimemsec})
    """   
    result = query_runner.execute_query(query=query)

    return result[0] # returning the first record (it's only 1 record in resultset by query design)

@pytest.fixture(scope='session')
def lambda_error_timestream_metrics_summary(region, start_epochtimemsec, stack_obj_for_naming):
    """
        Collects count of lambda errors
        Result is dict: e.g. {'errors': '2'}
    """
    DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
    TABLE_NAME = AWSNaming.TimestreamMetricsTable(
        stack_obj_for_naming, SettingConfigResourceTypes.LAMBDA_FUNCTIONS
    )

    client = boto3.client("timestream-query", region_name=region)
    query_runner = TimeStreamQueryRunner(client)

    query = f"""SELECT count(*) as errors
                FROM "{DB_NAME}"."{TABLE_NAME}"
                WHERE measure_name = 'error' AND time > from_milliseconds({start_epochtimemsec})
    """   
    result = query_runner.execute_query(query=query)

    return result[0] # returning the first record (it's only 1 record in resultset by query design)

#######################################################################################################################
@pytest.mark.skip
def test_alerts(test_results_messages):
    """
        Checking if correct notifications were sent
    """    
    msqchk = MessagesChecker(test_results_messages)

    cnt_lambda_error_messages = len(msqchk.subject_contains_all(["lambda_functions :", "FAILED"]))
    cnt_lambda_all_messages = len(msqchk.subject_contains_all(["lambda_functions :"]))
    
    assert cnt_lambda_error_messages == 1, "There should be exactly one lambda function error message"
    assert cnt_lambda_all_messages == 1, "There should be exactly one lambda function message"

@pytest.mark.skip
def test_timestream_records(lambda_execution_timestream_metrics_summary, lambda_error_timestream_metrics_summary):
    """
        Checking if timestream table is populated with correct data
    """
    executions = lambda_execution_timestream_metrics_summary.get('executions',0)
    errors = lambda_error_timestream_metrics_summary.get('errors',0)

    assert executions == '2', "There should be exactly 2 executions. One for each lambda function."
    assert errors == '1', "There should be exactly 1 failed execution."

@pytest.mark.skip
def test_digest_message(test_results_messages, config_reader, stack_obj_for_naming):
    """
        Checking if digest contains expected information
    """    
    msqchk = MessagesChecker(test_results_messages)

    digest_messages: list[IntegrationTestMessage] = msqchk.subject_contains_all(["Digest Report"])

    message_body = digest_messages[0].MessageBody
    
    # checking if there are mentions of testing stand glue jobs in the digest
    lambda_function_names = config_reader.get_names_by_resource_type(SettingConfigResourceTypes.LAMBDA_FUNCTIONS, stack_obj_for_naming)

    assert len(lambda_function_names) > 0, "There should be lambda functions in testing scope"

    for lambda_function_name in lambda_function_names:
        assert lambda_function_name in message_body, f"There should be mention of {lambda_function_name} lambda function"