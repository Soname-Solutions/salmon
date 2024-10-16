import time
import pytest
import os
import sys
import json
from pathlib import Path

# adding inttest_lib
parent_folder = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_folder)

# adding main lib
project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.dynamo_db_reader import IntegrationTestMessage, DynamoDBReader
from inttest_lib.common import (
    get_stack_obj_for_naming,
    TARGET_MEANING,
    CLOUDWATCH_ALERT_EVENTS_LOG_GROUP_MEANING,
)
from inttest_lib.inttests_config_reader import IntTests_Config_Reader
from lib.aws.aws_naming import AWSNaming
from lib.aws.cloudwatch_manager import CloudWatchManager


def pytest_addoption(parser):
    parser.addoption(
        "--start-epochtimemsec",
        action="store",
        default=None,
        help="Epoch time in milliseconds when the testing stand execution started",
    )
    parser.addoption(
        "--stage-name",
        action="store",
        default=None,
        help="stage-name where tests are conducted",
    )
    parser.addoption(
        "--region",
        action="store",
        default=None,
        help="AWS region where tests are conducted",
    )


@pytest.fixture(scope="session")
def start_epochtimemsec(request) -> int:
    return int(request.config.getoption("--start-epochtimemsec"))


@pytest.fixture(scope="session")
def stage_name(request):
    return request.config.getoption("--stage-name")


@pytest.fixture(scope="session")
def region(request):
    return request.config.getoption("--region")


@pytest.fixture(scope="session")
def stack_obj_for_naming(stage_name):
    return get_stack_obj_for_naming(stage_name=stage_name)


@pytest.fixture(scope="session")
def config_reader():
    return IntTests_Config_Reader()


@pytest.fixture(scope="session")
def test_results_messages(
    start_epochtimemsec, stack_obj_for_naming
) -> list[IntegrationTestMessage]:
    table_name = AWSNaming.DynamoDBTable(stack_obj_for_naming, TARGET_MEANING)
    reader = DynamoDBReader(table_name)
    messages: list[IntegrationTestMessage] = reader.get_all_messages()
    filtered_messages = [x for x in messages if x.SentTimestamp > start_epochtimemsec]
    return filtered_messages


@pytest.fixture(scope="session")
def cloudwatch_alerts_events(start_epochtimemsec, stack_obj_for_naming) -> list[str]:
    """
    Returns list of alert events
    (each record: { "event" : <json>, .. , "resource_name" : "glue_job1", "resource_type" : "glue_jobs })
    """
    log_group_name = AWSNaming.LogGroupName(
        stack_obj_for_naming, CLOUDWATCH_ALERT_EVENTS_LOG_GROUP_MEANING
    )
    mgr = CloudWatchManager()
    cur_time = int(time.time() * 1000)
    query_string = "fields @message"

    records = mgr.query_logs(
        log_group_name=log_group_name,
        query_string=query_string,
        start_time=start_epochtimemsec,
        end_time=cur_time,
    )

    outp = []
    for record in records:
        for field in record:
            if field["field"] == "@message":
                item = json.loads(field["value"])
                outp.append(item)

    return outp
