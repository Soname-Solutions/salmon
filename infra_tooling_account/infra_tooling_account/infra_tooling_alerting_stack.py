from aws_cdk import (
    Stack,
    Fn,
    IgnoreMode,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_lambda_destinations as lambda_destiantions,
    aws_iam as iam,
    aws_sns as sns,
    aws_sqs as sqs,
    Duration,
)
from constructs import Construct
import os
from lib.aws.aws_common_resources import AWSCommonResources

from lib.core.constants import CDKDeployExclusions, CDKResourceNames
from lib.aws.aws_naming import AWSNaming
from lib.settings.settings import Settings


class InfraToolingAlertingStack(Stack):
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

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
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

        super().__init__(scope, construct_id, **kwargs)

        input_settings_bucket_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "settings-bucket-arn")
        )

        input_timestream_database_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-storage-arn")
        )

        input_timestream_database_name = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-db-name")
        )

        input_timestream_alert_events_table_name = Fn.import_value(
            AWSNaming.CfnOutput(self, "alert-events-table-name")
        )

        input_notification_queue_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "notification-queue-arn")
        )

        input_internal_error_topic_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "internal-error-topic-arn")
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
            timestream_database_name=input_timestream_database_name,
            timestream_alert_events_table_name=input_timestream_alert_events_table_name,
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
            event_pattern=events.EventPattern(source=events.Match.prefix("aws")),
        )

        return alerting_bus, alerting_lambda_event_rule

    def create_alerting_lambda(
        self,
        settings_bucket: s3.Bucket,
        notification_queue: sqs.Queue,
        internal_error_topic: sns.Topic,
        timestream_database_arn: str,
        timestream_database_name: str,
        timestream_alert_events_table_name: str,
        alerting_lambda_event_rule: events.Rule,
    ) -> lambda_.Function:
        """Creates Lambda function for events alerting.

        Args:
            settings_bucket (s3.Bucket): Settings S3 Bucket
            notification_queue (sqs.Queue): SQS queue for notification messages
            internal_error_topic (sns.Topic): SNS topic for DLQ error alerts
            timestream_database_arn (str): ARN of the Timestream DB for alerts and metrics
            timestream_database_name (str): Name of the Timestream DB for alerts and metrics
            timestream_alert_events_table_name (str): Timestream table name for alert events
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
            iam.PolicyStatement(
                actions=["timestream:WriteRecords"],
                effect=iam.Effect.ALLOW,
                resources=[f"{timestream_database_arn}/table/*"],
            )
        )

        # required as per AWS Doc
        alerting_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:DescribeEndpoints"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        current_region = Stack.of(self).region
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
                "ALERT_EVENTS_DB_NAME": timestream_database_name,
                "ALERT_EVENTS_TABLE_NAME": timestream_alert_events_table_name,
            },
            role=alerting_lambda_role,
            retry_attempts=2,
            layers=[powertools_layer],
            on_failure=lambda_destiantions.SnsDestination(internal_error_topic),
        )

        # Alerting Lambda EventBridge Trigger
        alerting_lambda_event_rule.add_target(targets.LambdaFunction(alerting_lambda))

        return alerting_lambda
