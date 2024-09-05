import sys
import os
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from lib.core.constants import SettingConfigResourceTypes as types
from lib.aws.aws_naming import AWSNaming
from lib.aws.glue_manager import GlueManager


class IntTests_Config_Reader:
    def __init__(self, config_filename=None) -> None:
        if config_filename is None:
            config_filename = os.path.join(
                os.path.dirname(__file__), "..", "config.json"
            )

        with open(config_filename, "r") as config_file:
            self.config_data = json.load(config_file).get("scoped_resources", {})

    def get_meanings_by_resource_type(self, resource_type: str) -> list[str]:
        """
        Lists all resources of specific type which is in testing scope.
        Return not exactly the names of resources, but, for better compatibility - their "meanings"
        So fulle resources names should be reconstructed by AWSNaming.<Resource>(stack, meaning)
        """
        resource_items = self.config_data.get(resource_type, [])
        return [x["meaning"] for x in resource_items]

    def get_names_by_resource_type(self, resource_type: str, stack_obj_for_naming):
        resource_meanings = self.get_meanings_by_resource_type(resource_type)

        matches = {
            types.GLUE_JOBS: AWSNaming.GlueJob,
            types.LAMBDA_FUNCTIONS: AWSNaming.LambdaFunction,
            types.GLUE_WORKFLOWS: AWSNaming.GlueWorkflow,
            # todo: fill in the list
        }
        naming_func = matches[resource_type]

        return [
            naming_func(stack_obj_for_naming, meaning) for meaning in resource_meanings
        ]

    def get_glue_dq_meanings(self, context):
        """
        context parameter explanation:
        config item template: {"meaning" : "ts-dq-job-success", "containing_glue_job_meaning" : "aux-dq-job-success"}
        containing_glue_job_meaning is optional:
        containing_glue_job_meaning == None -> run standalone ()  context = GlueManager.DQ_Catalog_Context_Type
        containing_glue_job_meaning != None -> run standalone ()  context = GlueManager.DQ_Job_Context_Type

        returns two list (for glue_ruleset and glue_jobs meanings)
        if glue_jobs are not applicable - returns empty list
        """
        resource_type = types.GLUE_DATA_QUALITY
        need_job_attr = context == GlueManager.DQ_Job_Context_Type

        resource_items = self.config_data.get(resource_type, [])

        job_attr = "containing_glue_job_meaning"
        glue_rulesets = [
                x["meaning"]
                for x in resource_items
                if bool(x.get(job_attr, "")) == need_job_attr
            ]
        
        glue_jobs = [
                x.get(job_attr, "")
                for x in resource_items
                if bool(x.get(job_attr, "")) == need_job_attr and x.get(job_attr, "")
            ]

        return list(glue_rulesets), list(glue_jobs)

    def get_glue_dq_names(self, context, stack_obj_for_naming):
        glue_rulesets, glue_jobs = self.get_glue_dq_meanings(context)

        return (
            [
                AWSNaming.GlueRuleset(stack_obj_for_naming, meaning)
                for meaning in glue_rulesets
            ],
            [AWSNaming.GlueJob(stack_obj_for_naming, meaning) for meaning in glue_jobs]
        )
    
    def get_glue_workflow_child_glue_jobs_meanings(self, glue_workflow_meaning):
        gluewf_config = self.config_data.get(types.GLUE_WORKFLOWS,{})
        for gluewf in gluewf_config:
            if gluewf.get("meaning","") == glue_workflow_meaning:
                return [x["meaning"] for x in gluewf.get("glue_jobs",[])]
            
        return []

    def get_step_function_child_glue_jobs_meanings(self, step_function_meaning):
        gluewf_config = self.config_data.get(types.STEP_FUNCTIONS,{})
        for gluewf in gluewf_config:
            if gluewf.get("meaning","") == step_function_meaning:
                return [x["meaning"] for x in gluewf.get("glue_jobs",[])]
            
        return []