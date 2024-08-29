import argparse
import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.common import get_stack_obj_for_naming
from inttest_lib.inttests_config_reader import IntTests_Config_reader

from inttest_lib.runners.glue_job_runner import GlueJobRunner
from inttest_lib.runners.glue_dq_runner import GlueDQRunner
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner

from lib.core.constants import SettingConfigResourceTypes as types
from lib.aws.aws_naming import AWSNaming
from lib.aws.glue_manager import GlueManager

from inttest_lib.runners.glue_dq_runner import DQ_MEANING


def is_active(resource_type):
    settings = {
        types.GLUE_JOBS: True,
        types.GLUE_DATA_QUALITY: True,
        types.LAMBDA_FUNCTIONS: True,
    }
    return settings.get(resource_type, False)


def main():
    # for local debugging purposes
    current_epoch_msec = int(time.time()) * 1000
    print(
        f"Current time in epoch milliseconds: {current_epoch_msec}. Pytest param: --start-epochtimemsec={current_epoch_msec}"
    )

    # 1. prepare
    parser = argparse.ArgumentParser(description="Process some settings.")
    parser.add_argument("--stage-name", required=True, type=str, help="stage-name")
    parser.add_argument("--region", required=True, type=str, help="region")
    args = parser.parse_args()

    stage_name = args.stage_name
    region = args.region

    # 'mock' object, so we don't hardcode to-be-executed resource names, but use AWSNaming.<Service> methods
    # here it implements just required properties
    cfg_reader = IntTests_Config_reader()
    stack_obj_for_naming = get_stack_obj_for_naming(stage_name)

    # 2. run testing stand resources
    # 2.1 Glue Jobs
    if is_active(types.GLUE_JOBS):
        glue_job_names = cfg_reader.get_names_by_resource_type(
            types.GLUE_JOBS, stack_obj_for_naming
        )
        glue_job_runner = GlueJobRunner(
            resource_names=glue_job_names, region_name=region
        )

        glue_job_runner.initiate()

    # 2.2 Glue Data Quality
    if is_active(types.GLUE_DATA_QUALITY):
        # run Rulesets with GLUE_JOB context by triggering Glue DQ job
        _, glue_dq_job_names = cfg_reader.get_glue_dq_names(
            GlueManager.DQ_Job_Context_Type, stack_obj_for_naming
        )

        dq_glue_job_runner = GlueJobRunner(
            resource_names=glue_dq_job_names, region_name=region
        )

        dq_glue_job_runner.initiate()

        # run Rulesets with GLUE_DATA_CATALOG context
        glue_dq_ruleset_names, _ = cfg_reader.get_glue_dq_names(
            GlueManager.DQ_Catalog_Context_Type, stack_obj_for_naming
        )
        glue_dq_runner = GlueDQRunner(
            resource_names=glue_dq_ruleset_names,
            region_name=region,
            started_after_epoch_msec=current_epoch_msec,
            stack_obj_for_naming=stack_obj_for_naming,
        )
        glue_dq_runner.initiate()

    # 2.3
    if is_active(types.LAMBDA_FUNCTIONS):
        lambda_function_names = cfg_reader.get_names_by_resource_type(
            types.LAMBDA_FUNCTIONS, stack_obj_for_naming
        )
        lambda_runner = LambdaFunctionRunner(
            resource_names=lambda_function_names, region_name=region
        )
        lambda_runner.initiate()

    # 2.4 ... TBD other resource types

    # 3. awaiting resource completion
    if is_active(types.GLUE_JOBS):
        glue_job_runner.await_completion()
    if is_active(types.GLUE_DATA_QUALITY):
        dq_glue_job_runner.await_completion()
        glue_dq_runner.await_completion()
    if is_active(types.LAMBDA_FUNCTIONS):
        lambda_runner.await_completion()

    # 4. execute extract-metrics-orch lambda (in async mode, so if failure - destination would work)
    LAMBDA_METRICS_ORCH_NAME = AWSNaming.LambdaFunction(
        stack_obj_for_naming, "extract-metrics-orch"
    )
    lambda_orch_runner = LambdaFunctionRunner([LAMBDA_METRICS_ORCH_NAME], region)

    lambda_orch_runner.initiate()
    lambda_orch_runner.await_completion()

    # 5. execute digest lambda
    time.sleep(
        30
    )  # give some time for extract-metrics lambdas to complete and write metrics into timestream

    LAMBDA_DIGEST = AWSNaming.LambdaFunction(stack_obj_for_naming, "digest")
    lambda_digest_runner = LambdaFunctionRunner([LAMBDA_DIGEST], region)

    lambda_digest_runner.initiate()
    lambda_digest_runner.await_completion()


if __name__ == "__main__":
    main()
