from aws_cdk import (
    NestedStack,
    IgnoreMode,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_lambda_destinations as lambda_destiantions,
    aws_logs as cloudwatch_logs,
    aws_iam as iam,
    aws_sns as sns,
    aws_sqs as sqs,
    RemovalPolicy,
    Duration,
)
from constructs import Construct
import os
from lib.aws.aws_common_resources import AWSCommonResources

from lib.core.constants import CDKDeployExclusions, CDKResourceNames
from lib.aws.aws_naming import AWSNaming
from lib.settings.settings import Settings


class InfraToolingAlertingStack(NestedStack):
    """
    This class represents a stack for infrastructure tooling and alerting in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    Methods:
        create_event_bus(): Creates alerting event bus along with the rule to forward all AWS events
        create_alerting_lambda(s3.Bucket, sqs.Queue, sns.Topic, str, str, str, events.Rule):
            Creates Lambda function for events alerting.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        settings_bucket: s3.Bucket,
        internal_error_topic: sns.Topic,
        notification_queue: sqs.Queue,
        **kwargs,
    ) -> None:
        """
        Initialize the InfraToolingAlertingStack.

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
        self.settings_bucket = settings_bucket
        self.internal_error_topic = internal_error_topic
        self.notification_queue = notification_queue

        super().__init__(scope, construct_id, **kwargs)

        self.alerting_bus, alerting_lambda_event_rule = self.create_event_bus()

        self.log_group, self.log_stream = self.create_alert_events_log_stream()

        alerting_lambda = self.create_alerting_lambda(
            settings_bucket=self.settings_bucket,
            notification_queue=self.notification_queue,
            internal_error_topic=self.internal_error_topic,
            log_group_name=self.log_group.log_group_name,
            log_stream_name=self.log_stream.log_stream_name,
            alerting_lambda_event_rule=alerting_lambda_event_rule,
        )

    def create_event_bus(self) -> tuple[events.EventBus, events.Rule]:
        """Creates alerting event bus along with the rule to forward all AWS events.

        Returns:
            tuple[events.EventBus, events.Rule]: Alerting Event Bus with the Rule to forward all AWS events
        """
        alerting_bus = events.EventBus(
            self,
            "salmonAlertingBus",
            event_bus_name=AWSNaming.EventBus(self, CDKResourceNames.EVENTBUS_ALERTING),
        )

        # EventBridge bus resource policy
        monitored_account_ids = sorted(
            self.settings.get_monitored_account_ids(), reverse=True
        )
        # sorted is required. Otherwise, it shuffles Event Bus policy after each deploy

        monitored_principals = [
            iam.AccountPrincipal(account_id) for account_id in monitored_account_ids
        ]

        alerting_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid=AWSNaming.IAMPolicy(self, "AllowMonitoredAccountsPutEvents"),
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[alerting_bus.event_bus_arn],
                principals=monitored_principals,
            )
        )

        alerting_lambda_event_rule = events.Rule(
            self,
            "salmonAlertingLambdaEventRule",
            rule_name=AWSNaming.EventBusRule(self, "alerting-lambda"),
            event_bus=alerting_bus,
            event_pattern=events.EventPattern(
                source=events.Match.any_of(
                    events.Match.prefix("aws"), events.Match.prefix("salmon")
                )
            ),
        )

        return alerting_bus, alerting_lambda_event_rule

    def create_alert_events_log_stream(
        self,
    ) -> tuple[cloudwatch_logs.LogGroup, cloudwatch_logs.LogStream]:
        """Creates a log grop and a log stream in CloudWatch to store alert events.

        Returns:
            tuple[str, str]: Log group name and log stream name.
        """
        log_group = cloudwatch_logs.LogGroup(
            self,
            "salmonAlertEventsLogGroup",
            log_group_name=AWSNaming.LogGroupName(self, "alert-events"),
            removal_policy=RemovalPolicy.DESTROY,
            retention=cloudwatch_logs.RetentionDays.ONE_YEAR,
        )

        log_stream = cloudwatch_logs.LogStream(
            self,
            "salmonAlertEventsLogStream",
            log_group=log_group,
            log_stream_name=AWSNaming.LogStreamName(self, "alert-events"),
            removal_policy=RemovalPolicy.DESTROY,
        )

        return log_group, log_stream

    def create_alerting_lambda(
        self,
        settings_bucket: s3.Bucket,
        notification_queue: sqs.Queue,
        internal_error_topic: sns.Topic,
        log_group_name: str,
        log_stream_name: str,
        alerting_lambda_event_rule: events.Rule,
    ) -> lambda_.Function:
        """Creates Lambda function for events alerting.

        Args:
            settings_bucket (s3.Bucket): Settings S3 Bucket
            notification_queue (sqs.Queue): SQS queue for notification messages
            internal_error_topic (sns.Topic): SNS topic for DLQ error alerts
            log_group_name (str): Log group name to store alert events,
            log_stream_name (str): Log stream name to store alert events,
            alerting_lambda_event_rule (events.Rule): EventBridge rule which forwards AWS events

        Returns:
            lambda_.Function: Function responsible for alerting functionality
        """
        alerting_lambda_role = iam.Role(
            self,
            "alertingLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=AWSNaming.IAMRole(self, "alerting-lambda"),
        )

        alerting_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[f"{settings_bucket.bucket_arn}/*"],
            )
        )

        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sqs:SendMessage"],
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
            # to be able to enrich EMR Serverless alerts with EMR app name, job name, error message
            iam.PolicyStatement(
                actions=[
                    "emr-serverless:GetJobRun",
                    "emr-serverless:GetApplication",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
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

        alerting_lambda_path = "../src/"
        alerting_lambda = lambda_.Function(
            self,
            "salmonAlertingLambda",
            function_name=AWSNaming.LambdaFunction(self, "alerting"),
            code=lambda_.Code.from_asset(
                alerting_lambda_path,
                exclude=CDKDeployExclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_alerting.lambda_handler",
            timeout=Duration.seconds(120),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_PATH": f"s3://{settings_bucket.bucket_name}/settings/",
                "NOTIFICATION_QUEUE_URL": notification_queue.queue_url,
                "ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME": log_group_name,
                "ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME": log_stream_name,
            },
            role=alerting_lambda_role,
            retry_attempts=2,
            layers=[powertools_layer],
            on_failure=lambda_destiantions.SnsDestination(internal_error_topic),
        )

        # Alerting Lambda EventBridge Trigger
        alerting_lambda_event_rule.add_target(targets.LambdaFunction(alerting_lambda))

        return alerting_lambda
