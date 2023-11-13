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
    Duration,
    RemovalPolicy,
)
from constructs import Construct
import os
import json


class InfraToolingAlertingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        input_timestream_database_arn = Fn.import_value(
            f"output-{project_name}-metrics-events-storage-arn-{stage_name}"
        )

        # Settings S3 bucket
        settings_bucket_name = f"s3-{project_name}-settings-{stage_name}"
        settings_bucket = s3.Bucket(
            self,
            "salmonSettingsBucket",
            bucket_name=settings_bucket_name,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # S3 settings files deployment
        s3deploy.BucketDeployment(
            self,
            "salmonSettingsDeployment",
            sources=[s3deploy.Source.asset("../config/settings")],
            destination_bucket=settings_bucket,
            destination_key_prefix="settings",
        )

        # EventBridge Bus
        alerting_bus = events.EventBus(
            self,
            "salmonAlertingBus",
            event_bus_name=f"eventbus-{project_name}-alerting-{stage_name}",
        )

        # EventBridge bus resource policy
        # TODO: reuse existing settings reader
        general_settings_file_path = "../config/settings/general.json"
        with open(general_settings_file_path) as f:
            try:
                general_config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise json.decoder.JSONDecodeError(
                    f"Error parsing JSON file {general_settings_file_path}",
                    e.doc,
                    e.pos,
                )

        monitored_account_ids = set(
            [
                account["AccountId"]
                for account in general_config["monitored_environments"]
            ]
        )
        monitored_principals = [
            iam.AccountPrincipal(account_id) for account_id in monitored_account_ids
        ]

        alerting_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowMonitoredAccountsPutEvents",
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[alerting_bus.event_bus_arn],
                principals=monitored_principals,
            )
        )

        # Alerting Lambda Eventbridge rule
        alerting_lambda_event_rule = events.Rule(
            self,
            "salmonAlertingLambdaEventRule",
            rule_name=f"eventbusrule-{project_name}-alerting-lambda-{stage_name}",
            event_bus=alerting_bus,
            event_pattern=events.EventPattern(source=events.Match.prefix("aws")),
        )

        # Alerting Lambda Role
        alerting_lambda_role = iam.Role(
            self,
            "alertingLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{project_name}-alerting-lambda-{stage_name}",
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[settings_bucket.bucket_arn],
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:*"],
                effect=iam.Effect.ALLOW,
                resources=[input_timestream_database_arn],
            )
        )

        # Alerting Lambda
        alerting_lambda_path = os.path.join("../src/", "lambda/alerting-lambda")
        alerting_lambda = lambda_.Function(
            self,
            "salmonAlertingLambda",
            function_name=f"lambda-{project_name}-alerting-{stage_name}",
            code=lambda_.Code.from_asset(alerting_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(30),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={"SETTINGS_S3_BUCKET_NAME": settings_bucket_name},
            role=alerting_lambda_role,
        )

        # Alerting Lambda EventBridge Rule Target
        alerting_event_dlq = sqs.Queue(
            self,
            "alertingEventDlq",
            queue_name=f"queue-{project_name}-alerting-dlq-{stage_name}",
        )

        alerting_lambda_event_rule.add_target(
            targets.LambdaFunction(
                alerting_lambda,
                dead_letter_queue=alerting_event_dlq,
                retry_attempts=3,
            )
        )

        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)
