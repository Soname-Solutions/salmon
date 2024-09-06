import pytest
import boto3
from inttest_lib.dynamo_db_reader import IntegrationTestMessage
from inttest_lib.message_checker import MessagesChecker

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from lib.aws.timestream_manager import TimeStreamQueryRunner


@pytest.fixture(scope="session")
def emr_serverless_execution_timestream_metrics_summary(
    region, start_epochtimemsec, stack_obj_for_naming
):
    """
    Collects summary from relevant timestream table (records only since the test started are included).
    Result is dict: e.g. {'executions': '2', 'succeeded': '1', 'failed': '1'}
    """
    DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
    TABLE_NAME = AWSNaming.TimestreamMetricsTable(
        stack_obj_for_naming, SettingConfigResourceTypes.EMR_SERVERLESS
    )

    client = boto3.client("timestream-query", region_name=region)
    query_runner = TimeStreamQueryRunner(client)

    query = f"""SELECT sum(execution) as executions, sum(succeeded) as succeeded, sum(failed) as failed
                FROM "{DB_NAME}"."{TABLE_NAME}"
                WHERE time > from_milliseconds({start_epochtimemsec})
    """
    result = query_runner.execute_query(query=query)

    return result[
        0
    ]  # returning the first record (it's only 1 record in resultset by query design)


#######################################################################################################################
def test_alerts(test_results_messages):
    """
    Checking if correct notifications were sent
    """
    msqchk = MessagesChecker(test_results_messages)

    cnt_emr_serverless_error_messages = len(
        msqchk.subject_contains_all(["emr_serverless :", "FAILED"])
    )
    cnt_emr_serverless_all_messages = len(
        msqchk.subject_contains_all(["emr_serverless :"])
    )

    assert (
        cnt_emr_serverless_error_messages == 1
    ), "There should be exactly one emr serverless error message"
    assert (
        cnt_emr_serverless_all_messages == 1
    ), "There should be exactly one emr serverless job message"


def test_timestream_records(emr_serverless_execution_timestream_metrics_summary):
    """
    Checking if timestream table is populated with correct data
    """
    executions = emr_serverless_execution_timestream_metrics_summary.get(
        "executions", 0
    )
    succeeded = emr_serverless_execution_timestream_metrics_summary.get("succeeded", 0)
    failed = emr_serverless_execution_timestream_metrics_summary.get("failed", 0)

    assert (
        executions == "2"
    ), "There should be exactly 2 executions. One for each emr script."
    assert succeeded == "1", "There should be exactly 1 successful execution."
    assert failed == "1", "There should be exactly 1 failed execution."


def test_digest_message(test_results_messages, config_reader, stack_obj_for_naming):
    """
    Checking if digest contains expected information
    """
    msqchk = MessagesChecker(test_results_messages)

    digest_messages: list[IntegrationTestMessage] = msqchk.subject_contains_all(
        ["Digest Report"]
    )

    message_body = digest_messages[0].MessageBody

    # checking if there are mentions of testing stand glue jobs in the digest
    emr_serverless_job_names = config_reader.get_names_by_resource_type(
        SettingConfigResourceTypes.EMR_SERVERLESS, stack_obj_for_naming
    )

    assert (
        len(emr_serverless_job_names) > 0
    ), "There should be emr serverless apps in testing scope"

    for emr_serverless_job_name in emr_serverless_job_names:
        assert (
            emr_serverless_job_name in message_body
        ), f"There should be mention of {emr_serverless_job_name} emr serverless apps"
