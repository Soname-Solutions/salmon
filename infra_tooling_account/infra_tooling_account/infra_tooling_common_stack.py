from aws_cdk import (
    Stack,
    CfnOutput,
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

from lib.core.constants import CDKDeployExclusions, TimestreamRetention
from lib.aws.aws_naming import AWSNaming
from lib.settings.settings import Settings


class InfraToolingCommonStack(Stack):
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

        settings_bucket = self.create_settings_bucket()

        timestream_storage, kms_key = self.create_timestream_db()

        timestream_table_alert_events = self.create_timestream_tables(
            timestream_storage
        )

        timestream_table_alert_events.add_dependency(timestream_storage)

        # Internal Error SNS topic
        internal_error_topic = sns.Topic(
            self,
            "salmonInternalErrorTopic",
            topic_name=AWSNaming.SNSTopic(self, "internal-error"),
        )

        # Notification SQS Queue
        # TODO: confirm visibility timeout
        notification_queue = sqs.Queue(
            self,
            "salmonNotificationQueue",
            queue_name=AWSNaming.SQSQueue(self, "notification"),
            visibility_timeout=Duration.seconds(60),
        )

        notification_lambda = self.create_notification_lambda(
            internal_error_topic, notification_queue
        )

        output_settings_bucket_arn = CfnOutput(
            self,
            "salmonSettingsBucketArn",
            value=settings_bucket.bucket_arn,
            description="The ARN of the Settings S3 Bucket",
            export_name=AWSNaming.CfnOutput(self, "settings-bucket-arn"),
        )

        output_timestream_database_arn = CfnOutput(
            self,
            "salmonTimestreamDBArn",
            value=timestream_storage.attr_arn,
            description="The ARN of the Metrics and Events Storage",
            export_name=AWSNaming.CfnOutput(self, "metrics-events-storage-arn"),
        )

        output_timestream_database_name = CfnOutput(
            self,
            "salmonTimestreamDBName",
            value=timestream_storage.database_name,
            description="DB Name of the Metrics and Events Storage",
            export_name=AWSNaming.CfnOutput(self, "metrics-events-db-name"),
        )

        output_timestream_kms_key = CfnOutput(
            self,
            "salmonTimestreamKmsKey",
            value=kms_key.key_arn,
            description="Arn of KMS Key for Timestream DB",
            export_name=AWSNaming.CfnOutput(self, "metrics-events-kms-key-arn"),
        )        

        output_timestream_alerts_table_name = CfnOutput(
            self,
            "salmonTimestreamAlertsTableName",
            value=timestream_table_alert_events.table_name,
            description="Table Name for Alert Events storage",
            export_name=AWSNaming.CfnOutput(self, "alert-events-table-name"),
        )

        output_notification_queue_arn = CfnOutput(
            self,
            "salmonNotificationQueueArn",
            value=notification_queue.queue_arn,
            description="The ARN of the Notification SQS Queue",
            export_name=AWSNaming.CfnOutput(self, "notification-queue-arn"),
        )

        output_internal_error_topic_arn = CfnOutput(
            self,
            "salmonInternalErrorTopicArn",
            value=internal_error_topic.topic_arn,
            description="The ARN of the Internal Error Topic",
            export_name=AWSNaming.CfnOutput(self, "internal-error-topic-arn"),
        )

    def create_timestream_db(self) -> (timestream.CfnDatabase, kms.Key):
        """Creates Timestream database for events and metrics

        Returns:
            timestream.CfnDatabase: Timestream database
        """
        timestream_kms_key = kms.Key(
            self,
            "salmonTimestreamKMSKey",
            alias=AWSNaming.KMSKey(self, "timestream"),
            description="Key that protects Timestream data",
        )        
        timestream_storage = timestream.CfnDatabase(
            self,
            "salmonTimestreamDB",
            database_name=AWSNaming.TimestreamDB(self, "metrics-events-storage"),
            kms_key_id=timestream_kms_key.key_id,
        )

        return timestream_storage, timestream_kms_key

    def create_timestream_tables(
        self, timestream_storage: timestream.CfnDatabase
    ) -> timestream.CfnTable:
        """Creates necessary tables in Timestream DB

        Args:
            timestream_storage (timestream.CfnDatabase): Timestream database

        Returns:
            timestream.CfnTable: Alert Events table
        """
        # this part throws a warning, but applies correctly
        # waiting for the CDK fix: https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/1514
        retention_properties_property = timestream.CfnTable.RetentionPropertiesProperty(
            magnetic_store_retention_period_in_days=TimestreamRetention.MagneticStoreRetentionPeriodInDays,
            memory_store_retention_period_in_hours=TimestreamRetention.MemoryStoreRetentionPeriodInHours,
        )
        alert_events_table = timestream.CfnTable(
            self,
            "AlertEventsTable",
            database_name=timestream_storage.database_name,
            retention_properties=retention_properties_property,
            table_name=AWSNaming.TimestreamTable(self, "alert-events"),
        )

        return alert_events_table

    def create_settings_bucket(self) -> s3.Bucket:
        """Creates Settings files storage and uploads files from the local directory to it

        Returns:
            s3.Bucket: S3 Bucket with settings files
        """
        settings_bucket = s3.Bucket(
            self,
            "salmonSettingsBucket",
            bucket_name=AWSNaming.S3Bucket(self, "settings"),
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
                resources=[internal_error_topic.topic_arn],
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
            timeout=Duration.seconds(60),
            runtime=lambda_.Runtime.PYTHON_3_11,
            role=notification_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        notification_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(queue=notification_queue, batch_size=1)
        )

        return notification_lambda
