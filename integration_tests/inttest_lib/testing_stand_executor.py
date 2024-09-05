import os
import sys
import time

# Add the project root and lib path to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.common import get_stack_obj_for_naming
from inttest_lib.inttests_config_reader import IntTests_Config_Reader
from inttest_lib.runners.glue_job_runner import GlueJobRunner
from inttest_lib.runners.glue_dq_runner import GlueDQRunner
from inttest_lib.runners.glue_workflow_runner import GlueWorkflowRunner
from inttest_lib.runners.step_function_runner import StepFunctionRunner
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs
from lib.aws.aws_naming import AWSNaming
from lib.aws.glue_manager import GlueManager


class TestingStandExecutor:
    def __init__(self, stage_name, region, resource_types=None):
        self.stage_name = stage_name
        self.region = region
        self.cfg_reader = IntTests_Config_Reader()
        self.stack_obj_for_naming = get_stack_obj_for_naming(stage_name)
        self.runners = []

        # Parse and validate resource_types
        if resource_types.strip().lower() == "all":
            self.resource_types_to_run = SettingConfigs.RESOURCE_TYPES
        else:
            self.resource_types_to_run = [
                rt.strip() for rt in resource_types.split(",")
            ]

            # Validate provided resource types
            invalid_types = [
                rt
                for rt in self.resource_types_to_run
                if rt not in SettingConfigs.RESOURCE_TYPES
            ]
            if invalid_types:
                raise ValueError(
                    f"Invalid resource types provided: {', '.join(invalid_types)}. "
                    f"Valid types are: {', '.join(SettingConfigs.RESOURCE_TYPES)}"
                )

        # Explicitly remove LAMBDA_FUNCTIONS until tests are stable
        if types.LAMBDA_FUNCTIONS in self.resource_types_to_run:
            self.resource_types_to_run.remove(types.LAMBDA_FUNCTIONS)

        print(
            f"Testing stand execution for resources: {','.join(self.resource_types_to_run)}"
        )

    def run_workloads(self):
        # Glue Jobs
        if types.GLUE_JOBS in self.resource_types_to_run:
            glue_job_names = self.cfg_reader.get_names_by_resource_type(
                types.GLUE_JOBS, self.stack_obj_for_naming
            )
            glue_job_runner = GlueJobRunner(
                resource_names=glue_job_names, region_name=self.region
            )
            glue_job_runner.initiate()
            self.runners.append(glue_job_runner)

        # Glue Data Quality
        if types.GLUE_DATA_QUALITY in self.resource_types_to_run:
            _, glue_dq_job_names = self.cfg_reader.get_glue_dq_names(
                GlueManager.DQ_Job_Context_Type, self.stack_obj_for_naming
            )

            dq_glue_job_runner = GlueJobRunner(
                resource_names=glue_dq_job_names, region_name=self.region
            )
            dq_glue_job_runner.initiate()
            self.runners.append(dq_glue_job_runner)

            glue_dq_ruleset_names, _ = self.cfg_reader.get_glue_dq_names(
                GlueManager.DQ_Catalog_Context_Type, self.stack_obj_for_naming
            )
            glue_dq_runner = GlueDQRunner(
                resource_names=glue_dq_ruleset_names,
                region_name=self.region,
                started_after_epoch_msec=int(time.time()) * 1000,
                stack_obj_for_naming=self.stack_obj_for_naming,
            )
            glue_dq_runner.initiate()
            self.runners.append(glue_dq_runner)

        # Glue Workflows
        if types.GLUE_WORKFLOWS in self.resource_types_to_run:
            glue_workflow_names = self.cfg_reader.get_names_by_resource_type(
                types.GLUE_WORKFLOWS, self.stack_obj_for_naming
            )
            glue_workflow_runner = GlueWorkflowRunner(
                resource_names=glue_workflow_names, region_name=self.region
            )
            glue_workflow_runner.initiate()
            self.runners.append(glue_workflow_runner)

        # Step Functions
        if types.STEP_FUNCTIONS in self.resource_types_to_run:
            step_function_names = self.cfg_reader.get_names_by_resource_type(
                types.STEP_FUNCTIONS, self.stack_obj_for_naming
            )
            step_function_runner = StepFunctionRunner(
                resource_names=step_function_names, region_name=self.region
            )
            step_function_runner.initiate()
            self.runners.append(step_function_runner)            

        # Lambda Functions
        if types.LAMBDA_FUNCTIONS in self.resource_types_to_run:
            lambda_function_names = self.cfg_reader.get_names_by_resource_type(
                types.LAMBDA_FUNCTIONS, self.stack_obj_for_naming
            )
            lambda_runner = LambdaFunctionRunner(
                resource_names=lambda_function_names, region_name=self.region
            )
            lambda_runner.initiate()
            self.runners.append(lambda_runner)

    def await_workloads(self):
        for runner in self.runners:
            runner.await_completion()

    def conclude(self):
        LAMBDA_METRICS_ORCH_NAME = AWSNaming.LambdaFunction(
            self.stack_obj_for_naming, "extract-metrics-orch"
        )
        lambda_orch_runner = LambdaFunctionRunner(
            [LAMBDA_METRICS_ORCH_NAME], self.region
        )
        lambda_orch_runner.initiate()
        lambda_orch_runner.await_completion()

        time.sleep(30)  # give some time for extract-metrics lambdas to complete

        LAMBDA_DIGEST = AWSNaming.LambdaFunction(self.stack_obj_for_naming, "digest")
        lambda_digest_runner = LambdaFunctionRunner([LAMBDA_DIGEST], self.region)
        lambda_digest_runner.initiate()
        lambda_digest_runner.await_completion()
