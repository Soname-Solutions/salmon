import os
import sys
import boto3
from types import SimpleNamespace

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from lib.aws.timestream_manager import TimeStreamQueryRunner

stage_name = "devit"
stack_obj_for_naming = SimpleNamespace(project_name="salmon", stage_name=stage_name)

DB_NAME = AWSNaming.TimestreamDB(stack_obj_for_naming, "metrics-events-storage")
TABLE_NAME = AWSNaming.TimestreamMetricsTable(
    stack_obj_for_naming, SettingConfigResourceTypes.GLUE_JOBS
)

client = boto3.client("timestream-query")
query_runner = TimeStreamQueryRunner(client)

epoch_ms = 1723157446000

query = f"""SELECT sum(execution) as executions, sum(succeeded) as succeeded, sum(failed) as failed
             FROM "{DB_NAME}"."{TABLE_NAME}"
            WHERE time > from_milliseconds({epoch_ms})
"""
print(query)

result = query_runner.execute_query(query=query)
print(result)