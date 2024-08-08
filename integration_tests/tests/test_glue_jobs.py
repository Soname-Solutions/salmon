from types import SimpleNamespace
import pytest
import boto3
from inttest_lib.message_checker import MessagesChecker

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from lib.aws.timestream_manager import TimeStreamQueryRunner

@pytest.fixture(scope='session')
def glue_execution_timestream_metrics_summary(stage_name, region, start_epochtimemsec):
    """
        Collects summary from relevant timestream table (records only since the test started are included).
        Result is dict: e.g. {'executions': '2', 'succeeded': '1', 'failed': '1'}
    """
    stack_obj_for_naming = SimpleNamespace(project_name="salmon", stage_name=stage_name)

    DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
    TABLE_NAME = AWSNaming.TimestreamMetricsTable(
        stack_obj_for_naming, SettingConfigResourceTypes.GLUE_JOBS
    )

    client = boto3.client("timestream-query", region_name=region)
    query_runner = TimeStreamQueryRunner(client)

    query = f"""SELECT sum(execution) as executions, sum(succeeded) as succeeded, sum(failed) as failed
                FROM "{DB_NAME}"."{TABLE_NAME}"
                WHERE time > from_milliseconds({start_epochtimemsec})
    """   
    result = query_runner.execute_query(query=query)

    return result[0] # returning the first record (it's only 1 record in resultset by query design)


def test_sqs_messages(sqs_messages):
    """
        Checking if correct notifications were sent
    """    
    msqchk = MessagesChecker(sqs_messages)

    cnt_glue_error_messages = len(msqchk.subject_contains_all(["glue_jobs :", "FAILED"]))
    cnt_glue_all_messages = len(msqchk.subject_contains_all(["glue_jobs :"]))
    
    assert cnt_glue_error_messages == 1, "There should be exactly one glue job error message"
    assert cnt_glue_all_messages == 1, "There should be exactly one glue job message"

def test_timestream_records(glue_execution_timestream_metrics_summary):
    """
        Checking if timestream table is populated with correct data
    """
    executions = glue_execution_timestream_metrics_summary.get('executions',0)
    succeeded = glue_execution_timestream_metrics_summary.get('succeeded',0)
    failed = glue_execution_timestream_metrics_summary.get('failed',0)

    assert executions == '2', "There should be exactly 2 executions. One for each glue job."
    assert succeeded == '1', "There should be exactly 1 successful execution."
    assert failed == '1', "There should be exactly 1 failed execution."