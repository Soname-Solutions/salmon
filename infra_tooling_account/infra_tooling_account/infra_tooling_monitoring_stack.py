from aws_cdk import (
    Stack,
    Fn,
    IgnoreMode,
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

from lib.settings import settings_reader
from lib.constants import Exclusions


class InfraToolingMonitoringStack(Stack):
    """
    This class represents a stack for infrastructure tooling and monitoring in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    Methods:
        get_common_stack_references(): Retrieves references to artifacts created in common stack (like S3 bucket, SNS topic, ...)
        get_metrics_collection_interval_min(): Fetches the interval for metrics collection from general.json.
        create_extract_metrics_lambdas(settings_bucket, internal_error_topic, timestream_database_arn):
            Creates Lambda functions for extracting metrics.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the InfraToolingMonitoringStack.

        Args:
            scope (Construct): The CDK app or stack that this stack is a part of.
            id (str): The identifier for this stack.
            **kwargs: Arbitrary keyword arguments. Specifically looks for:
                - project_name (str): The name of the project. Used for naming resources. Defaults to None.
                - stage_name (str): The name of the deployment stage. Used for naming resources. Defaults to None.

        """
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        (
            settings_bucket,
            internal_error_topic,
            input_timestream_database_arn,
        ) = self.get_common_stack_references()

        (
            extract_metrics_orch_lambda,
            extract_metrics_lambda,
        ) = self.create_extract_metrics_lambdas(
            settings_bucket=settings_bucket,
            internal_error_topic=internal_error_topic,
            timestream_database_arn=input_timestream_database_arn,
        )

        metrics_collection_interval_min = self.get_metrics_collection_interval_min()

        rule = events.Rule(
            self,
            "MetricsExtractionScheduleRule",
            schedule=events.Schedule.rate(
                Duration.minutes(metrics_collection_interval_min)
            ),
            rule_name=f"rule-{self.project_name}-metrics-extract-cron-{self.stage_name}",
        )
        rule.add_target(targets.LambdaFunction(extract_metrics_orch_lambda))

    def get_common_stack_references(self):
        """
        Retrieves common stack references required for the stack's operations. These include the S3 bucket for settings,
        the ARN of the internal error SNS topic, and the Timestream database ARN.

        Returns:
            tuple: A tuple containing references to the settings S3 bucket, internal error topic, and Timestream database ARN.
        """
        input_settings_bucket_arn = Fn.import_value(
            f"output-{self.project_name}-settings-bucket-arn-{self.stage_name}"
        )

        input_timestream_database_arn = Fn.import_value(
            f"output-{self.project_name}-metrics-events-storage-arn-{self.stage_name}"
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

        # Internal Error Topic Import
        internal_error_topic = sns.Topic.from_topic_arn(
            self,
            "salmonInternalErrorTopic",
            topic_arn=input_internal_error_topic_arn,
        )

        return settings_bucket, internal_error_topic, input_timestream_database_arn

    def get_metrics_collection_interval_min(self):
        """
        Reads the metrics collection interval from a configuration file. The interval is defined in minutes.

        Returns:
            int: The interval in minutes for collecting metrics.

        Raises:
            Exception: If the 'metrics_collection_interval_min' key is not found in the configuration file.
        """
        # TODO: use settings validation
        general_settings_file_path = "../config/settings/general.json"
        with open(general_settings_file_path) as f:
            general_settings = settings_reader.GeneralSettingsReader(
                general_settings_file_path, f.read()
            )
            tooling_section = general_settings.get_tooling_environment()
            key = "metrics_collection_interval_min"
            if key in tooling_section:
                return tooling_section[key]
            else:
                raise Exception(
                    "metrics_collection_interval_min key not found in general.json config file ('tooling_environment' section)"
                )

    def create_extract_metrics_lambdas(
        self, settings_bucket, internal_error_topic, timestream_database_arn
    ):
        """
        Creates two AWS Lambda functions for extracting metrics. One function orchestrates the process,
        while the other performs the actual extraction of metrics.

        Parameters:
            settings_bucket (s3.Bucket): The S3 bucket containing settings.
            internal_error_topic (sns.Topic): The SNS topic for internal error notifications.
            timestream_database_arn (str): The ARN of the Timestream database for storing metrics.

        Returns:
            tuple: A tuple containing references to the orchestrator and extractor Lambda functions.
        """
        extract_metrics_lambda_role = iam.Role(
            self,
            "extract-metricsLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{self.project_name}-extract-metrics-lambda-{self.stage_name}",
        )

        extract_metrics_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        extract_metrics_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[settings_bucket.bucket_arn],
            )
        )

        extract_metrics_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                resources=[internal_error_topic.topic_arn],
            )
        )

        extract_metrics_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:*"],
                effect=iam.Effect.ALLOW,
                resources=[timestream_database_arn],
            )
        )

        extract_metrics_lambda_path = os.path.join("../src/")
        extract_metrics_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsLambda",
            function_name=f"lambda-{self.project_name}-extract-metrics-{self.stage_name}",
            code=lambda_.Code.from_asset(
                extract_metrics_lambda_path,
                exclude=Exclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_extract_metrics.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={"SETTINGS_S3_BUCKET_NAME": settings_bucket.bucket_name},
            role=extract_metrics_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        extract_metrics_orch_lambda_path = os.path.join("../src/")
        extract_metrics_orch_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsOrchLambda",
            function_name=f"lambda-{self.project_name}-extract-metrics-orch-{self.stage_name}",
            code=lambda_.Code.from_asset(
                extract_metrics_orch_lambda_path,
                exclude=Exclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_extract_metrics_orch.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={"SETTINGS_S3_BUCKET_NAME": settings_bucket.bucket_name},
            role=extract_metrics_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        return extract_metrics_orch_lambda, extract_metrics_lambda
