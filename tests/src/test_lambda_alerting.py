from unittest.mock import patch, MagicMock
import pytest
import os
from datetime import datetime, timezone, timedelta

from lambda_alerting import lambda_handler
from lib.core.constants import SettingConfigResourceTypes as resource_types, EventResult
from lib.settings import Settings
from lib.event_mapper.general_aws_event_mapper import ExecutionInfoUrlMixin
from lib.aws.lambda_manager import LambdaManager
from lib.aws.glue_manager import GlueManager

# uncomment this to see lambda's logging output
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# logger.addHandler(handler)

# RUNNING tests:
# pytest -q -s src/test_lambda_alerting.py
#
# or
# for specific resource_type
# pytest -q -s -k test_step_fun src/test_lambda_alerting.py

NOTIFICATION_MESSAGES_RESULT = {"result": "magic_mock"}

################################################################################################################################


@pytest.fixture(scope="session")
def os_vars_init(aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    stage_name = "teststage"
    os.environ["NOTIFICATION_QUEUE_URL"] = (
        f"https://sqs.{region}.amazonaws.com/{account_id}/queue-salmon-notification-{stage_name}.fifo"
    )
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME"] = (
        f"log-group-salmon-alert-events-{stage_name}"
    )
    os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME"] = (
        f"log-stream-salmon-alert-events-{stage_name}"
    )


@pytest.fixture(scope="session")
def event_dyn_props_init(aws_props_init):
    # Generates dynamic properties for events
    (account_id, region) = aws_props_init
    current_time = datetime.now() - timedelta(minutes=1)
    epoch_time = int(current_time.timestamp())
    time_str = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    version_str = current_time.strftime("%Y%m%d%H%M%S")

    return (account_id, region, time_str, epoch_time, version_str)


################################################################################################################################

# mocking AWS calls done in lambda_alerting


@pytest.fixture(scope="module", autouse=True)
def mock_settings(config_path):
    """
    A module-scoped fixture that automatically mocks Settings.from_s3_path
    to call Settings.from_file_path with a predetermined local path for all tests.
    """
    with patch(
        "lambda_alerting.Settings.from_s3_path",
        side_effect=lambda x: Settings.from_file_path(config_path),
    ) as _mock:
        yield _mock


@pytest.fixture(scope="module", autouse=True)
def mock_cloudwatch_writer():
    with patch(
        "lambda_alerting.CloudWatchAlertWriter.write_event_to_cloudwatch"
    ) as _mock:
        yield _mock


@pytest.fixture(scope="module", autouse=True)
def mock_send_messages_to_sqs():
    mocked_sqs_queue_sender = MagicMock()
    mocked_sqs_queue_sender.send_messages.return_value = NOTIFICATION_MESSAGES_RESULT
    with patch(
        "lambda_alerting.SQSQueueSender", return_value=mocked_sqs_queue_sender
    ) as _mock:
        yield _mock


@pytest.fixture(scope="module", autouse=True)
def mock_delivery_options():
    with patch(
        "lambda_alerting.DeliveryOptionsResolver.get_delivery_options",
        return_value=[{"delivery_method": "SES", "recipients": ["email@company.com"]}],
    ) as _mock:
        yield _mock


################################################################################################################################

# GLUE JOB tests


# Utility function to generate a Glue Job event with dynamic properties.
def get_glue_job_event(event_dyn_props, state, message):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    return {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "abcdef00-1234-5678-9abc-def012345678",
        "detail-type": "Glue Job State Change",
        "source": "aws.glue",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [],
        "detail": {
            "jobName": "glue-salmonts-pyjob-1-dev",
            "severity": "INFO",
            "state": state,  # "SUCCEEDED"/"FAILED",
            "jobRunId": "jr_abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            "message": message,  # "Job run succeeded", etc,
        },
    }


def test_glue_job1(os_vars_init, event_dyn_props_init):
    event = get_glue_job_event(event_dyn_props_init, "FAILED", "Job run failed")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_JOBS
    ), "Resouce type is incorrect"
    assert result["messages"], "Event should have messages"


def test_glue_job2(os_vars_init, event_dyn_props_init):
    event = get_glue_job_event(event_dyn_props_init, "SUCCEEDED", "Job run succeeded")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_JOBS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


def test_glue_job3(os_vars_init, event_dyn_props_init):
    event = get_glue_job_event(event_dyn_props_init, "RUNNING", "Job is running")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == False, "Event shouldn't be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_JOBS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################

# GLUE WORKFLOW tests


# Utility function to generate a Glue Workflow event with dynamic properties.
def get_glue_workflow_event(event_dyn_props, event_result):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    glue_workflow_event = {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "1c338584-7eb1-34e1-9f7d-f803fcb4ac22",
        "detail-type": "Glue Workflow State Change",
        "source": "salmon.glue_workflow",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [],
        "detail": {
            "workflowName": "glue-salmonts-workflow-dev",
            "state": "COMPLETED",  # boto3 declares 'RUNNING'|'COMPLETED'|'STOPPING'|'STOPPED'|'ERROR', but we see no 'ERROR' state
            "event_result": event_result,  # "SUCCESS" / "FAILURE",
            "workflowRunId": "wr_75b9bcd0d7753776161d4ca1c4badd1924b445961ccdb89ae5ab86e920e6bc87",
            "message": f"Test Workflow run execution status: {event_result.lower()}",
            "origin_account": account_id,
            "origin_region": region,
        },
    }
    return glue_workflow_event


def test_glue_workflow1(os_vars_init, event_dyn_props_init):
    event = get_glue_workflow_event(event_dyn_props_init, "FAILURE")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_WORKFLOWS
    ), "Resouce type is incorrect"
    assert result["messages"], "Event should have messages"


def test_glue_workflow2(os_vars_init, event_dyn_props_init):
    event = get_glue_workflow_event(event_dyn_props_init, "SUCCESS")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_WORKFLOWS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################

# STEP FUNCTIONS tests


# Utility function to generate a Glue Job event with dynamic properties.
def get_step_function_event(event_dyn_props, status, error_message=""):
    (account_id, region, time_str, epoch_time, version_str) = event_dyn_props

    return {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "614f23b5-d4ee-f0fb-1dcd-60b39fb1df23",
        "detail-type": "Step Functions Execution Status Change",
        "source": "aws.states",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [
            f"arn:aws:states:{region}:{account_id}:execution:stepfunction-salmonts-sample-dev2:6e60909a-42df-9468-42a1-bb3771b35ee2_8b8ae2c0-69a4-c760-1fb4-9698b049289c"
        ],
        "detail": {
            "executionArn": "arn:aws:states:{region}:{account_id}:execution:stepfunction-salmonts-sample-dev2:6e60909a-42df-9468-42a1-bb3771b35ee2_8b8ae2c0-69a4-c760-1fb4-9698b049289c",
            "stateMachineArn": "arn:aws:states:{region}:{account_id}:stateMachine:stepfunction-salmonts-sample-dev2",
            "name": "6e60909a-42df-9468-42a1-bb3771b35ee2_8b8ae2c0-69a4-c760-1fb4-9698b049289c",
            "status": status,  # "SUCCEEDED"/"FAILED"
            "startDate": epoch_time,
            "stopDate": (epoch_time + 5),
            "input": "not relevant",
            "output": "not relevant",
            "stateMachineVersionArn": "null",
            "stateMachineAliasArn": "null",
            "redriveCount": 0,
            "redriveDate": "null",
            "redriveStatus": "NOT_REDRIVABLE",
            "redriveStatusReason": "not relevant",
            "inputDetails": {"included": "true"},
            "outputDetails": {"included": "true"},
            "error": error_message,
            "cause": "null",
        },
    }


def test_step_function1(os_vars_init, event_dyn_props_init):
    event = get_step_function_event(event_dyn_props_init, "FAILED", "Exception occured")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.STEP_FUNCTIONS
    ), "Resouce type is incorrect"
    assert result["messages"], "Event should have messages"


def test_step_function2(os_vars_init, event_dyn_props_init):
    event = get_step_function_event(event_dyn_props_init, "SUCCEEDED")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.STEP_FUNCTIONS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


def test_step_function3(os_vars_init, event_dyn_props_init):
    event = get_step_function_event(event_dyn_props_init, "RUNNING")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == False, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.STEP_FUNCTIONS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################

# GLUE Crawler tests


# Utility function to generate a Glue Job event with dynamic properties.
def get_glue_crawler_event(event_dyn_props, state, message):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    return {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "7b14260c-421e-96e3-2c9b-e10682344fb5",
        "detail-type": "Glue Crawler State Change",
        "source": "aws.glue",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [],
        "detail": {
            "tablesCreated": "0",
            "warningMessage": "N/A",
            "partitionsUpdated": "0",
            "tablesUpdated": "0",
            "message": message,  # "Crawler Succeeded", "Crawler Failed"
            "partitionsDeleted": "0",
            "accountId": "405389362913",
            "runningTime (sec)": "62",
            "tablesDeleted": "0",
            "crawlerName": "glue-salmonts-crawler-dev",
            "completionDate": "2024-02-13T20:03:39Z",
            "state": state,  # "Succeeded", "Failed"
            "partitionsCreated": "0",
            "cloudWatchLogLink": "not relevant",
        },
    }


def test_glue_crawler1(os_vars_init, event_dyn_props_init):
    event = get_glue_crawler_event(event_dyn_props_init, "Failed", "Crawler Failed")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_CRAWLERS
    ), "Resouce type is incorrect"
    assert result["messages"], "Event should have messages"


def test_glue_crawler2(os_vars_init, event_dyn_props_init):
    event = get_glue_crawler_event(
        event_dyn_props_init, "Succeeded", "Crawler Succeeded"
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_CRAWLERS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################
# GLUE Data Catalog Database tests


# Utility function to generate a Glue Catalog (Database) event with dynamic properties.
def get_glue_catalog_database_event(event_dyn_props):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    return {
        "version": version_str,
        "id": "0131f87d-808a-2c56-ab53-108eaddc3a62",
        "detail-type": "Glue Data Catalog Database State Change",
        "source": "aws.glue",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [f"arn:aws:glue:{region}:{account_id}:database/testdb1"],
        "detail": {
            "databaseName": "testdb1",
            "typeOfChange": "CreateDatabase",
            "changedTables": [],
        },
    }


def test_glue_catalog_database1(os_vars_init, event_dyn_props_init):
    event = get_glue_catalog_database_event(event_dyn_props_init)

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_CATALOGS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################
# GLUE Data Catalog Table-level operation tests


# Utility function to generate a Glue Catalog (Table-level) event with dynamic properties.
def get_glue_catalog_table_event(event_dyn_props):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    return {
        "version": version_str,
        "id": "a91319ff-082e-f3ff-4f74-521c9685c0d4",
        "detail-type": "Glue Data Catalog Database State Change",
        "source": "aws.glue",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [f"arn:aws:glue:{region}:{account_id}:table/testdb1/tbl1"],
        "detail": {
            "databaseName": "testdb1",
            "typeOfChange": "CreateTable",
            "changedTables": ["tbl1"],
        },
    }


def test_glue_catalog_table1(os_vars_init, event_dyn_props_init):
    event = get_glue_catalog_table_event(event_dyn_props_init)

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_CATALOGS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################
# GLUE Data Catalog Column-level operation tests


# Utility function to generate a Glue Catalog (Column-level) event with dynamic properties.
def get_glue_catalog_column_event(event_dyn_props):
    (account_id, region, time_str, _, version_str) = event_dyn_props

    return {
        "version": version_str,
        "id": "330e4f27-c83c-59f3-247d-2c3e4f8a598c",
        "detail-type": "Glue Data Catalog Table State Change",
        "source": "aws.glue",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [f"arn:aws:glue:{region}:{account_id}:table/testdb1/tbl1"],
        "detail": {
            "databaseName": "testdb1",
            "changedPartitions": [],
            "typeOfChange": "UpdateTable",
            "tableName": "tbl1",
        },
    }


def test_glue_catalog_column1(os_vars_init, event_dyn_props_init):
    event = get_glue_catalog_column_event(event_dyn_props_init)

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_CATALOGS
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################

# LAMBDA FUNCTIONS tests


# Utility function to generate a Lambda Function event with dynamic properties.
def get_lambda_function_event(
    event_dyn_props, resource_name, status, event_result, message=""
):
    (account_id, region, time_str, epoch_time, version_str) = event_dyn_props

    return {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "c12129fe-97b6-fec0-a586-5624051b63eb",
        "detail-type": "Lambda Function Execution State Change",
        "source": "salmon.lambda",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [],
        "detail": {
            "lambdaName": resource_name,
            "state": status,  # "COMPLETED" / "FAILED"
            "event_result": event_result,  # "INFO" / "FAILURE",
            "message": message,
            "origin_account": account_id,
            "origin_region": region,
            "request_id": "c12129fe-97b6-fec0-a586-5624051b63eb",
        },
    }


def test_lambda_function_failed(os_vars_init, event_dyn_props_init):
    event = get_lambda_function_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="lambda-salmonts-sample1-dev",
        status=LambdaManager.LAMBDA_FAILURE_STATE,
        event_result=EventResult.FAILURE,
        message="[ERROR] Exception: intentional failure - lambda-sample1",
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.LAMBDA_FUNCTIONS
    ), "Resouce type is incorrect"

    assert result["execution_info_url"] == ExecutionInfoUrlMixin.get_url(
        resource_type=resource_types.LAMBDA_FUNCTIONS,
        region_name=event["detail"]["origin_region"],
        resource_name=event["detail"]["lambdaName"],
    ), "URL is incorrect"

    assert (
        LambdaManager.MESSAGE_PART_ERROR in event["detail"]["message"]
    ), "[ERROR] should be a part of the message"
    assert result["messages"], "Event should have messages"


def test_lambda_function_succeeded(os_vars_init, event_dyn_props_init):
    event = get_lambda_function_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="lambda-salmonts-sample2-dev",
        status=LambdaManager.LAMBDA_SUCCESS_STATE,
        event_result=EventResult.SUCCESS,
    )
    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.LAMBDA_FUNCTIONS
    ), "Resouce type is incorrect"

    assert result["execution_info_url"] == ExecutionInfoUrlMixin.get_url(
        resource_type=resource_types.LAMBDA_FUNCTIONS,
        region_name=event["detail"]["origin_region"],
        resource_name=event["detail"]["lambdaName"],
    ), "URL is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


def test_lambda_function_completed(os_vars_init, event_dyn_props_init):
    event = get_lambda_function_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="lambda-salmonts-sample3-dev",
        status="COMPLETED",
        event_result=EventResult.INFO,
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == False, "Event shouldn't be logged"
    assert (
        result["resource_type"] == resource_types.LAMBDA_FUNCTIONS
    ), "Resouce type is incorrect"

    assert result["execution_info_url"] == ExecutionInfoUrlMixin.get_url(
        resource_type=resource_types.LAMBDA_FUNCTIONS,
        region_name=event["detail"]["origin_region"],
        resource_name=event["detail"]["lambdaName"],
    ), "URL is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


################################################################################################################################

# Glue Data Quality tests


# Utility function to generate a Glue DQ event with dynamic properties.
def get_glue_dq_event(event_dyn_props, resource_name, status, event_result):
    (account_id, region, time_str, epoch_time, version_str) = event_dyn_props

    return {
        "version": version_str,  # instead of "normal" '0', we put here custom value, so we can track and find event in CloudWatch LogInsights
        "id": "1643c080-ab60-1171-65e1-f4fe17e5773e",
        "detail-type": "Data Quality Evaluation Results Available",
        "source": "aws.glue-dataquality",
        "account": account_id,
        "time": time_str,
        "region": region,
        "resources": [],
        "detail": {
            "rulesetNames": [resource_name],
            "state": status,  # "COMPLETED" / "FAILED"
            "event_result": event_result,  # "INFO" / "FAILURE",
            "context": {
                "catalogId": account_id,
                "contextType": GlueManager.DQ_Catalog_Context_Type,
                "databaseName": "test-glue-dq-db",
                "tableName": "test-glue-dq-table",
                "runId": "dqrun-823d27d644915f91833172789d4f3c9cc705d90d",
            },
        },
    }


def test_glue_dq_failed(os_vars_init, event_dyn_props_init):
    event = get_glue_dq_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="glue-salmonts-dq-ruleset-1",
        status="FAILED",
        event_result=EventResult.FAILURE,
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == True, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_QUALITY
    ), "Resouce type is incorrect"


def test_glue_dq_succeeded(os_vars_init, event_dyn_props_init):
    event = get_glue_dq_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="glue-salmonts-dq-ruleset-2",
        status="SUCCEEDED",
        event_result=EventResult.SUCCESS,
    )
    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_QUALITY
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"


def test_glue_dq_completed(os_vars_init, event_dyn_props_init):
    event = get_glue_dq_event(
        event_dyn_props=event_dyn_props_init,
        resource_name="glue-salmonts-dq-ruleset-3",
        status="COMPLETED",
        event_result=EventResult.INFO,
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == False, "Event shouldn't be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_DATA_QUALITY
    ), "Resouce type is incorrect"
    assert not (result["messages"]), "Event shouldn't have messages"
