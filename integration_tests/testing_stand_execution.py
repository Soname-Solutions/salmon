import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
lib_path = os.path.join(project_root, 'src')
sys.path.append(lib_path)

from inttest_lib.common import get_stack_obj_for_naming, get_testing_stand_resource_names
from inttest_lib.runners.glue_job_runner import GlueJobRunner
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner

from lib.core.constants import SettingConfigResourceTypes
from lib.aws.aws_naming import AWSNaming

def main():
    # for local debugging purposes
    import time
    current_epoch_seconds = int(time.time())*1000
    print(f"Current time in epoch seconds: {current_epoch_seconds}")

    # 1. prepare
    parser = argparse.ArgumentParser(description="Process some settings.")
    parser.add_argument("--stage-name", required=True, type=str, help="stage-name")
    parser.add_argument("--region", required=True, type=str, help="region")
    args = parser.parse_args()

    stage_name = args.stage_name
    region = args.region

    # 'mock' object, so we don't hardcode to-be-executed resource names, but use AWSNaming.<Service> methods
    # here it implements just required properties
    stack_obj_for_naming = get_stack_obj_for_naming(stage_name)

    TESTING_STAND_RESOURCES = get_testing_stand_resource_names(stage_name)

    # 2. run testing stand resources
    # 2.1 Glue Jobs
    glue_job_names = TESTING_STAND_RESOURCES[SettingConfigResourceTypes.GLUE_JOBS]
    runner = GlueJobRunner(resource_names = glue_job_names, region_name = region)

    runner.initiate()
    runner.await_completion()

    # 2.2 ... TBD other resource types

    # 3. execute extract-metrics-orch lambda (in async mode, so if failure - destination would work)
    LAMBDA_METRICS_ORCH_NAME = AWSNaming.LambdaFunction(stack_obj_for_naming, "extract-metrics-orch")
    lambda_orch_runner = LambdaFunctionRunner([LAMBDA_METRICS_ORCH_NAME], region)

    lambda_orch_runner.initiate()
    lambda_orch_runner.await_completion()

    # 4. execute digest lambda
    time.sleep(30) # give some time for extract-metrics lambdas to complete and write metrics into timestream

    LAMBDA_DIGEST = AWSNaming.LambdaFunction(stack_obj_for_naming, "digest")
    lambda_digest_runner = LambdaFunctionRunner([LAMBDA_DIGEST], region)

    lambda_digest_runner.initiate()
    lambda_digest_runner.await_completion()
   

if __name__ == "__main__":
    main()