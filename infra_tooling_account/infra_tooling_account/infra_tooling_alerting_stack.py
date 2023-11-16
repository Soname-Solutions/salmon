from aws_cdk import (
    Stack,
    Fn,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sns as sns,
    aws_sqs as sqs,
    Duration,
)
from constructs import Construct
import os
import json


class InfraToolingAlertingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        input_settings_bucket_arn = Fn.import_value(
            f"output-{self.project_name}-settings-bucket-arn-{self.stage_name}"
        )

        input_timestream_database_arn = Fn.import_value(
            f"output-{self.project_name}-metrics-events-storage-arn-{self.stage_name}"
        )

        input_notification_queue_arn = Fn.import_value(
            f"output-{self.project_name}-notification-queue-arn-{self.stage_name}"
        )

        input_internal_error_topic_arn = Fn.import_value(
            f"output-{self.project_name}-internal-error-topic-arn-{self.stage_name}"
        )

        # Settings S3 Bucket Import
        settings_bucket = s3.Bucket.from_bucket_arn(
            self,
            "salmonSettingsBucket",
            bucket_arn=input_settings_bucket_arn,
        )

        # Notification Queue Import
        notification_queue = sqs.Queue.from_queue_arn(
            self,
            "salmonNotificationQueue",
            queue_arn=input_notification_queue_arn,
        )

        # Internal Error Topic Import
        internal_error_topic = sns.Topic.from_topic_arn(
            self,
            "salmonInternalErrorTopic",
            topic_arn=input_internal_error_topic_arn,
        )

        alerting_bus, alerting_lambda_event_rule = self.create_event_bus()

        alerting_lambda = self.create_alerting_lambda(
            settings_bucket=settings_bucket,
            notification_queue=notification_queue,
            internal_error_topic=internal_error_topic,
            timestream_database_arn=input_timestream_database_arn,
            alerting_lambda_event_rule=alerting_lambda_event_rule,
        )

    def create_event_bus(self):
        alerting_bus = events.EventBus(
            self,
            "salmonAlertingBus",
            event_bus_name=f"eventbus-{self.project_name}-alerting-{self.stage_name}",
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
                account["account_id"]
                for account in general_config["monitored_environments"]
            ]
        )
        monitored_principals = [
            iam.AccountPrincipal(account_id) for account_id in monitored_account_ids
        ]

        alerting_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid=f"policy-{self.project_name}-AllowMonitoredAccountsPutEvents-{self.stage_name}",
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[alerting_bus.event_bus_arn],
                principals=monitored_principals,
            )
        )

        alerting_lambda_event_rule = events.Rule(
            self,
            "salmonAlertingLambdaEventRule",
            rule_name=f"eventbusrule-{self.project_name}-alerting-lambda-{self.stage_name}",
            event_bus=alerting_bus,
            event_pattern=events.EventPattern(source=events.Match.prefix("aws")),
        )

        return alerting_bus, alerting_lambda_event_rule

    def create_alerting_lambda(
        self,
        settings_bucket,
        notification_queue,
        internal_error_topic,
        timestream_database_arn,
        alerting_lambda_event_rule,
    ):
        alerting_lambda_role = iam.Role(
            self,
            "alertingLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{self.project_name}-alerting-lambda-{self.stage_name}",
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
                actions=["queue:SendMessage"],
                effect=iam.Effect.ALLOW,
                resources=[notification_queue.queue_arn],
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                resources=[internal_error_topic.topic_arn],
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:*"],
                effect=iam.Effect.ALLOW,
                resources=[timestream_database_arn],
            )
        )

        alerting_lambda_path = os.path.join("../src/", "lambda/alerting-lambda")
        alerting_lambda = lambda_.Function(
            self,
            "salmonAlertingLambda",
            function_name=f"lambda-{self.project_name}-alerting-{self.stage_name}",
            code=lambda_.Code.from_asset(alerting_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(30),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_BUCKET_NAME": settings_bucket.bucket_name,
                "NOTIFICATION_QUEUE_NAME": notification_queue.queue_name,
            },
            role=alerting_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        # Alerting Lambda EventBridge Trigger
        alerting_lambda_event_rule.add_target(targets.LambdaFunction(alerting_lambda))

        return alerting_lambda
