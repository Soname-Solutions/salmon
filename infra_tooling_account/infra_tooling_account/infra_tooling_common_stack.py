from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
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


class InfraToolingCommonStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        settings_bucket = self.create_settings_bucket()

        timestream_storage = self.create_timestream_db()

        timestream_table_alert_events = self.create_timestream_tables(
            timestream_storage
        )

        # Internal Error SNS topic
        internal_error_topic = sns.Topic(
            self,
            "salmonInternalErrorTopic",
            topic_name=f"topic-{self.project_name}-internal-error-{self.stage_name}",
        )

        # Notification SQS Queue
        # TODO: confirm visibility timeout
        notification_queue = sqs.Queue(
            self,
            "salmonNotificationQueue",
            queue_name=f"queue-{self.project_name}-notification-{self.stage_name}",
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
            export_name=f"output-{self.project_name}-settings-bucket-arn-{self.stage_name}",
        )

        output_timestream_database_arn = CfnOutput(
            self,
            "salmonTimestreamDBArn",
            value=timestream_storage.attr_arn,
            description="The ARN of the Metrics and Events Storage",
            export_name=f"output-{self.project_name}-metrics-events-storage-arn-{self.stage_name}",
        )

        output_timestream_database_name = CfnOutput(
            self,
            "salmonTimestreamDBName",
            value=timestream_storage.database_name,
            description="DB Name of the Metrics and Events Storage",
            export_name=f"output-{self.project_name}-metrics-events-db-name-{self.stage_name}",
        )

        output_timestream_alerts_table_name = CfnOutput(
            self,
            "salmonTimestreamAlertsTableName",
            value=timestream_table_alert_events.table_name,
            description="Table Name for Alert Events storage",
            export_name=f"output-{self.project_name}-alert-events-table-name-{self.stage_name}",
        )

        output_notification_queue_arn = CfnOutput(
            self,
            "salmonNotificationQueueArn",
            value=notification_queue.queue_arn,
            description="The ARN of the Notification SQS Queue",
            export_name=f"output-{self.project_name}-notification-queue-arn-{self.stage_name}",
        )

        output_internal_error_topic_arn = CfnOutput(
            self,
            "salmonInternalErrorTopicArn",
            value=internal_error_topic.topic_arn,
            description="The ARN of the Internal Error Topic",
            export_name=f"output-{self.project_name}-internal-error-topic-arn-{self.stage_name}",
        )

    def create_timestream_db(self):
        timestream_kms_key = kms.Key(
            self,
            "salmonTimestreamKMSKey",
            alias=f"key-{self.project_name}-timestream-{self.stage_name}",
            description="Key that protects Timestream data",
        )
        timestream_storage = timestream.CfnDatabase(
            self,
            "salmonTimestreamDB",
            database_name=f"timestream-{self.project_name}-metrics-events-storage-{self.stage_name}",
            kms_key_id=timestream_kms_key.key_id,
        )

        return timestream_storage

    def create_timestream_tables(self, timestream_storage):
        retention_properties_property = timestream.CfnTable.RetentionPropertiesProperty(
            magnetic_store_retention_period_in_days="365",
            memory_store_retention_period_in_hours="240",
        )
        alert_events_table = timestream.CfnTable(
            self,
            "AlertEventsTable",
            database_name=timestream_storage.database_name,
            retention_properties=retention_properties_property,
            table_name="alert-events",
        )

        return alert_events_table

    def create_settings_bucket(self):
        settings_bucket = s3.Bucket(
            self,
            "salmonSettingsBucket",
            bucket_name=f"s3-{self.project_name}-settings-{self.stage_name}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
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

    def create_notification_lambda(self, internal_error_topic, notification_queue):
        notification_lambda_role = iam.Role(
            self,
            "salmonNotificationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{self.project_name}-notification-lambda-{self.stage_name}",
        )

        notification_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        notification_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
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

        notification_lambda_path = os.path.join("../src/", "lambda/notification-lambda")
        notification_lambda = lambda_.Function(
            self,
            "salmonNotificationLambda",
            function_name=f"lambda-{self.project_name}-notification-{self.stage_name}",
            code=lambda_.Code.from_asset(notification_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(60),
            runtime=lambda_.Runtime.PYTHON_3_11,
            role=notification_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        notification_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(notification_queue)
        )

        return notification_lambda
