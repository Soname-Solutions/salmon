import argparse
import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.common import (
    get_stack_obj_for_naming,
    get_testing_stand_resource_names,
)
from inttest_lib.runners.glue_job_runner import GlueJobRunner
from inttest_lib.runners.glue_dq_runner import GlueDQRunner
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner

from lib.core.constants import SettingConfigResourceTypes as types
from lib.aws.aws_naming import AWSNaming
from lib.aws.glue_manager import GlueManager

from inttest_lib.runners.glue_dq_runner import DQ_MEANING


def main():
    # for local debugging purposes
    current_epoch_msec = int(time.time()) * 1000
    print(f"Current time in epoch milliseconds: {current_epoch_msec}. Pytest param: --start-epochtimemsec={current_epoch_msec}")

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
    glue_job_names = TESTING_STAND_RESOURCES[types.GLUE_JOBS]
    glue_job_runner = GlueJobRunner(resource_names=glue_job_names, region_name=region)

    glue_job_runner.initiate()

    # 2.2 Glue Data Quality
    # run Rulesets with GLUE_JOB context by triggering Glue DQ job
    glue_dq_job_names = TESTING_STAND_RESOURCES[types.GLUE_DATA_QUALITY][
        GlueManager.DQ_Job_Context_Type
    ]
    dq_glue_job_runner = GlueJobRunner(resource_names=glue_dq_job_names, region_name=region)

    dq_glue_job_runner.initiate()

    # run Rulesets with GLUE_DATA_CATALOG context
    glue_dq_ruleset_names = TESTING_STAND_RESOURCES[types.GLUE_DATA_QUALITY][
        GlueManager.DQ_Catalog_Context_Type
    ]
    glue_dq_runner = GlueDQRunner(
        resource_names=glue_dq_ruleset_names,
        region_name=region,
        started_after_epoch_msec=current_epoch_msec,
        stack_obj_for_naming=stack_obj_for_naming,
    )
    glue_dq_runner.initiate()
   
    # 2.3 ... TBD other resource types
    glue_job_runner.await_completion()    
    dq_glue_job_runner.await_completion()
    glue_dq_runner.await_completion()

    # 3. execute extract-metrics-orch lambda (in async mode, so if failure - destination would work)
    LAMBDA_METRICS_ORCH_NAME = AWSNaming.LambdaFunction(
        stack_obj_for_naming, "extract-metrics-orch"
    )
    lambda_orch_runner = LambdaFunctionRunner([LAMBDA_METRICS_ORCH_NAME], region)

    lambda_orch_runner.initiate()
    lambda_orch_runner.await_completion()

    # 4. execute digest lambda
    time.sleep(
        30
    )  # give some time for extract-metrics lambdas to complete and write metrics into timestream

    LAMBDA_DIGEST = AWSNaming.LambdaFunction(stack_obj_for_naming, "digest")
    lambda_digest_runner = LambdaFunctionRunner([LAMBDA_DIGEST], region)

    lambda_digest_runner.initiate()
    lambda_digest_runner.await_completion()


if __name__ == "__main__":
    main()
