from aws_cdk import (
    Stack,
    Tags,
    aws_glue_alpha as glue,
    aws_glue as glue_old,
)
from aws_cdk.aws_s3_assets import Asset
from constructs import Construct
import os
from .lib_cdk_sample_resources import iam as iam_helper
from .lib_cdk_sample_resources import glue as glue_helper

SRC_FOLDER_NAME = "../src_testing_stand/"

class TestingStandStack(Stack):
    """
    Stack creates sample monitored resources for Salmon integration tests

    Attributes:
        project_name (str): The name of the project, used in naming resources.
        stage_name (str): The stage or environment name, used in naming resources.
    """

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        self.project_name = kwargs.pop("project_name", None)
        self.stage_name = kwargs.pop("stage_name", None)
        super().__init__(scope, id, **kwargs)

        # IAM Role
        glue_iam_role = iam_helper.create_glue_iam_role(
            scope=self,
            role_id="GlueIAMRole",
            role_name=f"iamr-{self.project_name}-glue-role-{self.stage_name}",
        )

        # Creating two sample Python Shell glue job ("one", "two")
        job_items = ["success", "fail"]
        glue_jobs = []
        for job_item in job_items:
            job_id = f"GlueJob{job_item.capitalize()}"
            job_name = f"glue-{self.project_name}-pyjob-{job_item}-{self.stage_name}"
            job_script = glue.Code.from_asset(
                os.path.join(SRC_FOLDER_NAME, f"glue-sparkjob-{job_item}.py")
            )
            # calling helper to create a job
            glue_job_tmp = glue_helper.create_pyspark_glue_job(
                scope=self,
                job_id=job_id,
                job_name=job_name,
                role=glue_iam_role,
                script=job_script,
                default_arguments={}
            )
            glue_jobs.append(glue_job_tmp)
