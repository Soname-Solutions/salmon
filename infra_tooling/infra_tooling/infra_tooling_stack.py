from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_events as events,
    Tags,
    aws_lambda as lambda_,
    aws_events_targets as targets,
    Duration,
)
from constructs import Construct
import os


class InfraToolingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

        stage = kwargs.pop("stage", None)
        project_name = kwargs.pop("project_name", None)

        project_root_path =  os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        super().__init__(scope, construct_id, **kwargs)

        settings_bucket = s3.Bucket(
            self, 
            "salmonSettingsBucket", 
            bucket_name=f"s3-{project_name}-settings-{stage}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
            )

        notification_bus = events.EventBus(
            self, 
            "salmonNotificationsBus",
            event_bus_name=f"bus-{project_name}-notification-{stage}"
            )

        notification_lambda_path = os.path.join('../src/', 'lambda/notification-lambda')
        notification_lambda = lambda_.Function(
            self,
            "salmonNotificationLambda",
            function_name=f"lambda-{project_name}-notification-{stage}",
            code=lambda_.Code.from_asset(notification_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(30),
            runtime=lambda_.Runtime.PYTHON_3_11,
        )

        Tags.of(self).add("stage", stage)
        Tags.of(self).add("project_name", project_name)

