from aws_cdk import (
    NestedStack,
    Duration,
    IgnoreMode,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    aws_kms as kms,
    aws_iam as iam,
    aws_timestream as timestream,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sns as sns,
)
from constructs import Construct
import os

from lib.core.constants import CDKDeployExclusions
from lib.aws.aws_naming import AWSNaming
from lib.aws.aws_common_resources import AWSCommonResources
from lib.settings.settings import Settings


class InfraToolingCommonStack(NestedStack):
    """
    This class represents a stack for infrastructure tooling and common functionality in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    Methods:
        create_timestream_db(): Creates Timestream database for events and metrics
        create_timestream_tables(timestream.CfnDatabase): Creates necessary tables in Timestream DB
        create_settings_bucket(): Creates Settings files storage and uploads files to it
        create_notification_lambda(sns.Topic, sqs.Queue): Creates Lambda function for notification functionality
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the InfraToolingCommonStack.

        Args:
            scope (Construct): The CDK app or stack that this stack is a part of.
            id (str): The identifier for this stack.
            **kwargs: Arbitrary keyword arguments. Specifically looks for:
                - project_name (str): The name of the project. Used for naming resources. Defaults to None.
                - stage_name (str): The name of the deployment stage. Used for naming resources. Defaults to None.

        """
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)
        self.settings: Settings = kwargs.pop("settings", None)

        super().__init__(scope, construct_id, **kwargs)

        self.settings_bucket = self.create_settings_bucket()

        self.timestream_storage, self.timestream_kms_key = self.create_timestream_db()

        # Internal Error SNS topic
        self.internal_error_topic = sns.Topic(
            self,
            "salmonInternalErrorTopic",
            topic_name=AWSNaming.SNSTopic(self, "internal-error"),
        )

        # Notification FIFO SQS Queue
        # TODO: confirm visibility timeout
        self.notification_queue = sqs.Queue(
            self,
            "salmonNotificationQueue",
            content_based_deduplication=True,
            fifo=True,
            queue_name=AWSNaming.SQSQueue(self, "notification"),
            visibility_timeout=Duration.seconds(60),
        )

        notification_lambda = self.create_notification_lambda(
            self.internal_error_topic, self.notification_queue
        )

    def create_timestream_db(self) -> tuple[timestream.CfnDatabase, kms.Key]:
        """Creates Timestream database for events and metrics

        Returns:
            timestream.CfnDatabase: Timestream database
        """
        timestream_kms_key = kms.Key(
            self,
            "salmonTimestreamKMSKey",
            alias=AWSNaming.KMSKey(self, "timestream"),
            description="Key that protects Timestream data",
            removal_policy=RemovalPolicy.DESTROY,
        )
        timestream_storage = timestream.CfnDatabase(
            self,
            "salmonTimestreamDB",
            database_name=AWSNaming.TimestreamDB(self, "metrics-events-storage"),
            kms_key_id=timestream_kms_key.key_id,
        )

        return timestream_storage, timestream_kms_key

    def create_settings_bucket(self) -> s3.Bucket:
        """Creates Settings files storage and uploads files from the local directory to it

        Returns:
            s3.Bucket: S3 Bucket with settings files
        """
        settings_bucket = s3.Bucket(
            self,
            "salmonSettingsBucket",
            bucket_name=AWSNaming.S3Bucket(
                self, "settings", NestedStack.of(self).account
            ),
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        s3deploy.BucketDeployment(
            self,
            "salmonSettingsDeployment",
            sources=[s3deploy.Source.asset("../config/settings")],
            destination_bucket=settings_bucket,
            destination_key_prefix="settings",
            exclude=[".gitignore"],
        )

        return settings_bucket

    def create_notification_lambda(
        self, internal_error_topic: sns.Topic, notification_queue: sqs.Queue
    ) -> lambda_.Function:
        """Creates Lambda function for notification functionality

        Args:
            internal_error_topic (sns.Topic): SNS Topic for DLQ alerts
            notification_queue (sqs.Queue): SQS queue as the input for notification lambda

        Returns:
            lambda_.Function: Notification Lambda
        """
        notification_lambda_role = iam.Role(
            self,
            "salmonNotificationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=AWSNaming.IAMRole(self, "notification-lambda"),
        )

        notification_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ses:ListIdentities",
                    "ses:GetIdentityVerificationAttributes",
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                ],  # referring to '*' instead of internal_error_topic.topic_arn as there might be SNS way of regular
                # notification configured, so need to publish to arbitrary topics.
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:ChangeMessageVisibility",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ReceiveMessage",
                ],
                effect=iam.Effect.ALLOW,
                resources=[notification_queue.queue_arn],
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sns:Publish",
                ],
                effect=iam.Effect.ALLOW,
                resources=[internal_error_topic.topic_arn],
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                effect=iam.Effect.ALLOW,
                resources=[
                    "*"
                ],  # to be able to retrieve Secrets required for SMTP sender
            )
        )

        current_region = NestedStack.of(self).region
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            id="lambda-powertools",
            layer_version_arn=AWSCommonResources.get_lambda_powertools_layer_arn(
                current_region
            ),
        )

        notification_lambda_path = os.path.join("../src/")
        notification_lambda = lambda_.Function(
            self,
            "salmonNotificationLambda",
            function_name=AWSNaming.LambdaFunction(self, "notification"),
            code=lambda_.Code.from_asset(
                notification_lambda_path,
                exclude=CDKDeployExclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_notification.lambda_handler",
            environment={
                "INTERNAL_ERROR_TOPIC_ARN": internal_error_topic.topic_arn,
            },
            layers=[powertools_layer],
            timeout=Duration.seconds(60),
            runtime=lambda_.Runtime.PYTHON_3_11,
            role=notification_lambda_role,
            retry_attempts=2,
            # no destinations configuration because destinations do not support SQS lambda event source
        )

        notification_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(queue=notification_queue, batch_size=1)
        )

        return notification_lambda
