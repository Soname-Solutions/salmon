from aws_cdk import (
    RemovalPolicy,
    Stack,
    Tags,
    aws_glue_alpha as glue,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda as _lambda,
)
from aws_cdk.aws_s3_assets import Asset
from constructs import Construct
import os
import boto3
from .lib_cdk_sample_resources import iam as iam_helper
from .lib_cdk_sample_resources import glue as glue_helper

from inttest_lib.common import (
    TARGET_MEANING,
    get_target_sns_topic_name,
    get_resource_name_meanings,
)

from lib.aws.aws_naming import AWSNaming
from lib.aws.aws_common_resources import SNS_TOPIC_INTERNAL_ERROR_MEANING
from lib.core.constants import SettingConfigResourceTypes

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

        # Creating sample glue jobs (list - in from ../config.json)
        glue_job_meanings = get_resource_name_meanings(SettingConfigResourceTypes.GLUE_JOBS)
        glue_jobs = []
        for glue_job_meaning in glue_job_meanings:
            job_id = f"GlueJob{glue_job_meaning.capitalize()}"
            job_name = AWSNaming.GlueJob(self, glue_job_meaning)
            job_script = glue.Code.from_asset(
                os.path.join(SRC_FOLDER_NAME, "glue_jobs", f"{glue_job_meaning}.py")
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

        # Create target DynamoDB table
        target_table_name = AWSNaming.DynamoDBTable(self, TARGET_MEANING)
        messages_table = dynamodb.Table(
            self,
            "MessagesTable",
            partition_key=dynamodb.Attribute(
                name="MessageId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="Timestamp", type=dynamodb.AttributeType.NUMBER
            ),
            table_name=target_table_name,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY, 
        )        

        # Create a Lambda function
        lambda_function = _lambda.Function(
            self,
            "LambdaForwardToSQS",
            runtime=_lambda.Runtime.PYTHON_3_11,
            function_name=AWSNaming.LambdaFunction(self, "inttest-to-dynamo"),
            handler="index.handler",
            code=_lambda.Code.from_inline(
                """
import json
import boto3
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)
dynamodb = boto3.client('dynamodb')

def handler(event, context):
    logger.info(f"event = {event}")
    table_name = '"""
                + messages_table.table_name
                + """'
    for record in event['Records']:
        sns_data = record['Sns']
        message_id = sns_data.get('MessageId','N/A')
        message_body = sns_data.get('Message','Message body is not found')
        subject = sns_data.get('Subject','No subject')
        timestamp = int(time.time())*1000

        message = {
            'MessageId': {'S': message_id},
            'Subject': {'S': subject},
            'MessageBody': {'S': message_body},
            'Timestamp': {'N': str(timestamp)}
        }

        dynamodb.put_item(
            TableName=table_name,
            Item=message
        )
    return {"statusCode": 200, "body": json.dumps('Success')}
                """
            ),            
        )

        messages_table.grant_write_data(lambda_function)        

        # Add the Lambda function as a subscription to the target SNS topic
        target_topic.add_subscription(subs.LambdaSubscription(lambda_function))

        # Add Lambda subscription to Internal-errors topic
        sns_client = boto3.client("sns")
        current_region = Stack.of(self).region
        current_account = Stack.of(self).account
        internal_error_topic_name = AWSNaming.SNSTopic(
            self, SNS_TOPIC_INTERNAL_ERROR_MEANING
        )
        internal_error_topic_arn = f"arn:aws:sns:{current_region}:{current_account}:{internal_error_topic_name}"

        internal_error_sns_topic = sns.Topic.from_topic_arn(
            self, "importedTopic", topic_arn=internal_error_topic_arn
        )

        internal_error_sns_topic.add_subscription(
            subs.LambdaSubscription(lambda_function)
        )
