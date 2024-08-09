import os
import sys
import boto3

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import SettingConfigResourceTypes
from lib.aws.timestream_manager import TimeStreamQueryRunner


from inttest_lib.common import get_stack_obj_for_naming, get_testing_stand_resource_names

stage_name = "devit"
region = "eu-central-1"

stack_obj_for_naming = get_stack_obj_for_naming(stage_name)

TESTING_STAND_RESOURCES = get_testing_stand_resource_names(stage_name)

print(TESTING_STAND_RESOURCES)