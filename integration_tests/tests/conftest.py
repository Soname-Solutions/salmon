from types import SimpleNamespace
import pytest
import os
import sys
from pathlib import Path

# adding inttest_lib
parent_folder = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_folder)

# adding main lib
project_root = str(Path(__file__).resolve().parent.parent.parent)
#os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.sqs_queue_reader import SqsMessage, SQSQueueReader
from inttest_lib.common import get_stack_obj_for_naming, get_testing_stand_resource_names

def pytest_addoption(parser):
    parser.addoption(
        "--start-epochtimemsec", action="store", default=None, help="Epoch time in milliseconds when the testing stand execution started"
    )
    parser.addoption(
        "--stage-name", action="store", default=None, help="stage-name where tests are conducted"
    )
    parser.addoption(
        "--region", action="store", default=None, help="AWS region where tests are conducted"
    )    

@pytest.fixture(scope='session')
def start_epochtimemsec(request) -> int:
    return int(request.config.getoption("--start-epochtimemsec"))

@pytest.fixture(scope='session')
def stage_name(request):
    return request.config.getoption("--stage-name")

@pytest.fixture(scope='session')
def region(request):
    return request.config.getoption("--region")

@pytest.fixture(scope='session')
def stack_obj_for_naming(stage_name):
    return get_stack_obj_for_naming(stage_name=stage_name)

@pytest.fixture(scope='session')
def testing_stand_resource_names(stage_name):
    return get_testing_stand_resource_names(stage_name=stage_name)

@pytest.fixture(scope='session')
def sqs_messages(start_epochtimemsec, stage_name, region) -> list[SqsMessage]:
    queue_name = f"queue-salmon-inttest-target-{stage_name}.fifo"
    queue_url = SQSQueueReader.get_queue_url_from_name(queue_name, region)
    reader = SQSQueueReader(queue_url)
    messages: list[SqsMessage] = reader.get_all_messages()
    filtered_messages = [x for x in messages if x.SentTimestamp > start_epochtimemsec]
    return filtered_messages

