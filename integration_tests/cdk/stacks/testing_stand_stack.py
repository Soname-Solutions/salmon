from aws_cdk import (
    Stack,
    Tags,
    aws_glue_alpha as glue,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_sqs as sqs,
    aws_lambda as _lambda,
)
from aws_cdk.aws_s3_assets import Asset
from constructs import Construct
import os
import boto3
from .lib_cdk_sample_resources import iam as iam_helper
from .lib_cdk_sample_resources import glue as glue_helper
from lib.aws.aws_naming import AWSNaming
from inttest_lib.common import TARGET_MEANING, get_target_sns_topic_name
from lib.aws.sns_manager import SnsHelper

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
            role_name=AWSNaming.IAMRole(self, "glue-role"),
        )

        # Creating two sample Python Shell glue job ("one", "two")
        job_items = ["success", "fail"]
        glue_jobs = []
        for job_item in job_items:
            job_id = f"GlueJob{job_item.capitalize()}"
            job_name = AWSNaming.GlueJob(self, f"pyjob-{job_item}")
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
                default_arguments={},
            )
            glue_jobs.append(glue_job_tmp)

        topic_name = get_target_sns_topic_name(self.stage_name)
        target_topic = sns.Topic(
            self, "TargetSNSTopic", display_name=topic_name, topic_name=topic_name
        )

        # Create an SQS queue
        target_queue = sqs.Queue(
            self,
            "TargetSQSQueue",
            content_based_deduplication=True,
            fifo=True,
            queue_name=AWSNaming.SQSQueue(self, TARGET_MEANING),
        )

        # Create a Lambda function
        lambda_function = _lambda.Function(
            self,
            "LambdaForwardToSQS",
            runtime=_lambda.Runtime.PYTHON_3_11,
            function_name=AWSNaming.LambdaFunction(self, "inttest-to-sqs"),
            handler="index.handler",
            code=_lambda.Code.from_inline(
                """
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sqs = boto3.client('sqs')

def handler(event, context):
    logger.info(f"event = {event}")
    queue_url = '"""
                + target_queue.queue_url
                + """'
    for record in event['Records']:
        sns_data = record['Sns']
        message_id = sns_data.get('MessageId','N/A')
        message_body = sns_data.get('Message','Message body is not found')
        subject = sns_data.get('Subject','No subject')
        message = {
            'Id': message_id,
            'Subject': subject,
            'MessageBody': message_body
        }
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
            MessageGroupId='integration-tests'
        )
    return {"statusCode": 200, "body": json.dumps('Success')}
                """
            ),
        )

        # Grant the Lambda function permissions to send messages to the SQS queue
        target_queue.grant_send_messages(lambda_function)

        # Add the Lambda function as a subscription to the target SNS topic
        target_topic.add_subscription(subs.LambdaSubscription(lambda_function))

        # Add Lambda subscription to Internal-errors topic
        sns_client = boto3.client("sns")
        internal_error_topic_name = AWSNaming.SNSTopic(self, "internal-error")
        internal_error_topic_arn = SnsHelper.get_topic_arn_by_name(
            sns_client=sns_client, topic_name=internal_error_topic_name
        )
        internal_error_sns_topic = sns.Topic.from_topic_arn(
            self, "importedTopic", topic_arn=internal_error_topic_arn
        )

        internal_error_sns_topic.add_subscription(
            subs.LambdaSubscription(lambda_function)
        )
