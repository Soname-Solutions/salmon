from aws_cdk import (
    Stack,
    Fn,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    Tags,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3_deployment as s3deploy,
    aws_sqs as sqs,
    Duration
)
from constructs import Construct
import os


class InfraToolingAlertingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)
        
        input_timestream_database_arn = Fn.import_value(f"output-{project_name}-metrics-events-storage-arn-{stage_name}")


        # Settings S3 bucket
        settings_bucket_name = f"s3-{project_name}-settings-{stage_name}"
        settings_bucket = s3.Bucket(
            self,
            "salmonSettingsBucket",
            bucket_name=settings_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # S3 settings files deployment
        s3deploy.BucketDeployment(
            self, "salmonSettingsDeployment",
            sources=[s3deploy.Source.asset('../config/settings')],
            destination_bucket=settings_bucket,
            destination_key_prefix='settings'
        )

        # EventBridge Bus
        notification_bus = events.EventBus(
            self,
            "salmonNotificationsBus",
            event_bus_name=f"eventbus-{project_name}-notification-{stage_name}"
        )

        # Notification Lambda Eventbridge rule
        notification_lambda_event_rule = events.Rule(
            self,
            "salmonNotificationLambdaEventRule",
            rule_name=f"eventbusrule-{
                project_name}-notification-lambda-{stage_name}",
            event_bus=notification_bus,
            event_pattern=events.EventPattern(source=events.Match.prefix("aws"))
        )

        # Notification Lambda Role
        notification_lambda_role = iam.Role(
            self, "notificationLambdaRole",
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name=f"role-{project_name}-notification-lambda-{stage_name}"
        )

        notification_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject"],
            effect=iam.Effect.ALLOW,
            resources=[settings_bucket.bucket_arn],
        ))

        notification_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["ses:SendEmail", "ses:SendRawEmail"],
            effect=iam.Effect.ALLOW,
            resources=["*"]
        ))
        
        notification_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["timestream:*"],
            effect=iam.Effect.ALLOW,
            resources=[input_timestream_database_arn]
        ))

        # Notification Lambda
        notification_lambda_path = os.path.join(
            '../src/', 'lambda/notification-lambda')
        notification_lambda = lambda_.Function(
            self,
            "salmonNotificationLambda",
            function_name=f"lambda-{project_name}-notification-{stage_name}",
            code=lambda_.Code.from_asset(notification_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(30),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={'SETTINGS_S3_BUCKET_NAME': settings_bucket_name},
            role=notification_lambda_role
        )

        # Notification Lambda EventBridge Rule Target
        notification_event_dlq = sqs.Queue(
            self,
            "notificationEventDlq",
            queue_name=f"queue-{project_name}-notification-dlq-{stage_name}"
        )

        notification_lambda_event_rule.add_target(
            targets.LambdaFunction(
                notification_lambda,
                dead_letter_queue=notification_event_dlq,
                retry_attempts=3
            )
        )

        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)
