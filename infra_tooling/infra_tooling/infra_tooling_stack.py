from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_events as events,
    Tags,
    aws_lambda as lambda_,
    aws_events_targets as targets,
    aws_iam as iam,
    Duration
)
from constructs import Construct
import os


class InfraToolingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)

        project_root_path =  os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        super().__init__(scope, construct_id, **kwargs)

        # Settings S3 bucket
        settings_bucket_name = f"s3-{project_name}-settings-{stage_name}"
        settings_bucket = s3.Bucket(
            self, 
            "salmonSettingsBucket", 
            bucket_name=settings_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
            )


        # EventBridge Bus
        notification_bus = events.EventBus(
            self, 
            "salmonNotificationsBus",
            event_bus_name=f"bus-{project_name}-notification-{stage_name}"
            )


        # Notification Lambda Role
        notification_lambda_role = iam.Role(
            self, "notificationLambdaRole",
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            role_name=f"role-{project_name}-notification-lambda-{stage_name}"
        )

        settings_bucket_arn = f'arn:aws:s3:::{settings_bucket_name}/*'
        notification_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject"],
            effect=iam.Effect.ALLOW,
            resources=[settings_bucket_arn],
        ))

        notification_lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["ses:SendEmail", "ses:SendRawEmail"],
            effect=iam.Effect.ALLOW,
            resources=["*"]
        ))


        # Notification Lambda
        notification_lambda_path = os.path.join('../src/', 'lambda/notification-lambda')
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

        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)

