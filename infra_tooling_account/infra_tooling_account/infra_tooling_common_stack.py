from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    Tags,
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
        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        # AWS Timestream DB
        timestream_kms_key = kms.Key(
            self,
            "salmonTimestreamKMSKey",
            alias=f"key-{project_name}-timestream-{stage_name}",
            description="Key that protects Timestream data",
        )
        timestream_storage = timestream.CfnDatabase(
            self,
            "salmonTimestreamDB",
            database_name=f"timestream-{project_name}-metrics-events-storage-{stage_name}",
            kms_key_id=timestream_kms_key.key_id,
        )

        # Internal Error SNS topic
        internal_error_topic = sns.Topic(
            self,
            "salmonInternalErrorTopic",
            topic_name=f"topic-{project_name}-internal-error-{stage_name}",
        )

        # Notification SQS Queue
        # TODO: confirm visibility timeout
        notification_queue = sqs.Queue(
            self,
            "salmonNotificationQueue",
            queue_name=f"queue-{project_name}-notification-{stage_name}",
            visibility_timeout=Duration.seconds(60),
        )

        # Notification Lambda Role
        notification_lambda_role = iam.Role(
            self,
            "salmonNotificationLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{project_name}-notification-lambda-{stage_name}",
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

        # Notification Lambda
        notification_lambda_path = os.path.join("../src/", "lambda/notification-lambda")
        notification_lambda = lambda_.Function(
            self,
            "salmonNotificationLambda",
            function_name=f"lambda-{project_name}-notification-{stage_name}",
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

        # Output Timestream DB Arn
        output_timestream_database_arn = CfnOutput(
            self,
            "salmonTimestreamDBArn",
            value=timestream_storage.attr_arn,
            description="The ARN of the Metrics and Events Storage",
            export_name=f"output-{project_name}-metrics-events-storage-arn-{stage_name}",
        )

        # Output Notification SQS Queue Arn
        output_notification_queue_arn = CfnOutput(
            self,
            "salmonNotificationQueueArn",
            value=notification_queue.queue_arn,
            description="The ARN of the Notification SQS Queue",
            export_name=f"output-{project_name}-notification-queue-arn-{stage_name}",
        )

        output_internal_error_topic_arn = CfnOutput(
            self,
            "salmonInternalErrorTopicArn",
            value=internal_error_topic.topic_arn,
            description="The ARN of the Internal Error Topic",
            export_name=f"output-{project_name}-internal-error-topic-arn-{stage_name}",
        )

        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)
