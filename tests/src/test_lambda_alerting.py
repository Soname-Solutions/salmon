import pytest
import os
from datetime import datetime, timezone, timedelta

from lambda_alerting import lambda_handler
from lib.core.constants import SettingConfigResourceTypes as resource_types, EventResult
from lib.settings import Settings
from lib.event_mapper.impl.general_aws_event_mapper import ExecutionInfoUrlMixin
from lib.aws.lambda_manager import LambdaManager

# uncomment this to see lambda's logging output
# import logging
# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# logger.addHandler(handler)

# RUNNING tests:
# pytest -q -s --stage-name <<your_env_name_here>> src/test_lambda_alerting.py
#
# or
# for specific resource_type
# pytest -q -s -k test_step_fun --stage-name <<your_env_name_here>> src/test_lambda_alerting.py

################################################################################################################################


@pytest.fixture(scope="session")
def aws_props_init():
    # Inits AWS acc id and region (from local settings -> tooling env)
    file_path = "../config/settings/"
    settings = Settings.from_file_path(file_path)
    account_id, region = settings.get_tooling_account_props()

    return (account_id, region)


@pytest.fixture(scope="session")
def os_vars_init(stage_name, aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    os.environ["NOTIFICATION_QUEUE_URL"] = (
        f"https://sqs.{region}.amazonaws.com/{account_id}/queue-salmon-notification-{stage_name}.fifo"
    )
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ[
        "ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME"
    ] = f"log-group-salmon-alert-events-{stage_name}"
    os.environ[
        "ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME"
    ] = f"log-stream-salmon-alert-events-{stage_name}"


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


def test_glue_job2(os_vars_init, event_dyn_props_init):
    event = get_glue_job_event(event_dyn_props_init, "SUCCEEDED", "Job run succeeded")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_JOBS
    ), "Resouce type is incorrect"


def test_glue_job3(os_vars_init, event_dyn_props_init):
    event = get_glue_job_event(event_dyn_props_init, "RUNNING", "Job is running")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == False, "Event shouldn't be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_JOBS
    ), "Resouce type is incorrect"


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


def test_glue_workflow2(os_vars_init, event_dyn_props_init):
    event = get_glue_workflow_event(event_dyn_props_init, "SUCCESS")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event shouldn't raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_WORKFLOWS
    ), "Resouce type is incorrect"


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


def test_step_function2(os_vars_init, event_dyn_props_init):
    event = get_step_function_event(event_dyn_props_init, "SUCCEEDED")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.STEP_FUNCTIONS
    ), "Resouce type is incorrect"


def test_step_function3(os_vars_init, event_dyn_props_init):
    event = get_step_function_event(event_dyn_props_init, "RUNNING")

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event should raise alert"
    assert result["event_is_monitorable"] == False, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.STEP_FUNCTIONS
    ), "Resouce type is incorrect"


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


def test_glue_crawler2(os_vars_init, event_dyn_props_init):
    event = get_glue_crawler_event(
        event_dyn_props_init, "Succeeded", "Crawler Succeeded"
    )

    result = lambda_handler(event, {})

    assert result["event_is_alertable"] == False, "Event should raise alert"
    assert result["event_is_monitorable"] == True, "Event should be logged"
    assert (
        result["resource_type"] == resource_types.GLUE_CRAWLERS
    ), "Resouce type is incorrect"


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
