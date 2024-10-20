import os
import sys
import time

# Add the project root and lib path to sys.path
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.common import get_stack_obj_for_naming
from inttest_lib.inttests_config_reader import IntTests_Config_Reader
from inttest_lib.runners.glue_job_runner import GlueJobRunner
from inttest_lib.runners.glue_crawler_runner import GlueCrawlerRunner
from inttest_lib.runners.glue_dq_runner import GlueDQRunner
from inttest_lib.runners.glue_workflow_runner import GlueWorkflowRunner
from inttest_lib.runners.step_function_runner import StepFunctionRunner
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner
from inttest_lib.runners.emr_serverless_runner import (
    EMRServerlessJobRunner,
    get_scripts_s3_bucket_meaning,
    EXEC_IAM_ROLE_MEANING,
)
from lib.core.constants import SettingConfigResourceTypes as types, SettingConfigs
from lib.aws.aws_naming import AWSNaming
from lib.aws.glue_manager import GlueManager
from lib.aws.emr_manager import EMRManager
from lib.aws.sts_manager import StsManager


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
            lambda_resources_data = (
                self.cfg_reader.get_lambda_meanings_with_retry_attempts()
            )
            lambda_runner = LambdaFunctionRunner(
                resources_data=lambda_resources_data,
                region_name=self.region,
                stack_obj=self.stack_obj_for_naming,
            )
            lambda_runner.initiate()
            self.runners.append(lambda_runner)

        # EMR Serverless
        if types.EMR_SERVERLESS in self.resource_types_to_run:
            # get dict { app : [script_paths]}
            emr_resources_data = self.cfg_reader.get_emr_serverless_apps_with_scripts(
                self.stack_obj_for_naming
            )

            account_id = StsManager().get_account_id()
            # get scripts s3 bucket name
            scripts_s3_bucket = AWSNaming.S3Bucket(
                self.stack_obj_for_naming, get_scripts_s3_bucket_meaning(account_id)
            )

            # get EMR exec role arn
            emr_exec_role_name = AWSNaming.IAMRole(
                self.stack_obj_for_naming, EXEC_IAM_ROLE_MEANING
            )
            emr_exec_role_arn = AWSNaming.Arn_IAMRole(
                self.stack_obj_for_naming, account_id, emr_exec_role_name
            )

            runner = EMRServerlessJobRunner(
                emr_resources_data, self.region, emr_exec_role_arn, scripts_s3_bucket
            )
            runner.initiate()
            self.runners.append(runner)

        # Glue Crawlers
        if types.GLUE_CRAWLERS in self.resource_types_to_run:
            glue_crawler_names = self.cfg_reader.get_names_by_resource_type(
                types.GLUE_CRAWLERS, self.stack_obj_for_naming
            )

            runner = GlueCrawlerRunner(
                resource_names=glue_crawler_names, region_name=self.region
            )
            runner.initiate()
            self.runners.append(runner)

    def await_workloads(self):
        for runner in self.runners:
            runner.await_completion()

    def conclude(self):
        lambda_orch_retry_attempts = 0
        lambda_orch_meaning = "extract-metrics-orch"
        lambda_orch_runner = LambdaFunctionRunner(
            resources_data={lambda_orch_meaning: lambda_orch_retry_attempts},
            region_name=self.region,
            stack_obj=self.stack_obj_for_naming,
        )
        lambda_orch_runner.initiate()
        lambda_orch_runner.await_completion()

        time.sleep(30)  # give some time for extract-metrics lambdas to complete

        lambda_digest_retry_attempts = 0
        lambda_digest_meaning = "digest"
        lambda_digest_runner = LambdaFunctionRunner(
            resources_data={lambda_digest_meaning: lambda_digest_retry_attempts},
            region_name=self.region,
            stack_obj=self.stack_obj_for_naming,
        )
        lambda_digest_runner.initiate()
        lambda_digest_runner.await_completion()
