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
    aws_timestream as timestream,
    Duration,
)
from constructs import Construct
import os

from lib.core.constants import CDKDeployExclusions, CDKResourceNames
from lib.aws.aws_naming import AWSNaming
from lib.aws.aws_common_resources import AWS_Common_Resources
from lib.settings.settings import Settings
from lib.core.constants import CDKResourceNames, TimestreamRetention


class InfraToolingMonitoringStack(Stack):
    """
    This class represents a stack for infrastructure tooling and monitoring in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    Methods:
        get_common_stack_references(): Retrieves references to artifacts created in common stack (like S3 bucket, SNS topic, ...)
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
        self.settings: Settings = kwargs.pop("settings", None)

        super().__init__(scope, construct_id, **kwargs)

        (
            settings_bucket,
            internal_error_topic,
            input_timestream_database_arn,
            input_timestream_database_name,
        ) = self.get_common_stack_references()

        (
            extract_metrics_orch_lambda,
            extract_metrics_lambda,
        ) = self.create_extract_metrics_lambdas(
            settings_bucket=settings_bucket,
            internal_error_topic=internal_error_topic,
            timestream_database_arn=input_timestream_database_arn,
        )

        # Create table for metrics storage (1 per service)
        self.create_metrics_tables(timestream_database_name=input_timestream_database_name)

        metrics_collection_interval_min = (
            self.settings.get_metrics_collection_interval_min()
        )

        rule = events.Rule(
            self,
            "MetricsExtractionScheduleRule",
            schedule=events.Schedule.rate(
                Duration.minutes(metrics_collection_interval_min)
            ),
            rule_name=AWSNaming.EventBusRule(self, "metrics-extract-cron"),
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
            AWSNaming.CfnOutput(self, "settings-bucket-arn")
        )

        input_timestream_database_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-storage-arn")
        )

        input_timestream_database_name = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-db-name")
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

        # Internal Error Topic Import
        internal_error_topic = sns.Topic.from_topic_arn(
            self,
            "salmonInternalErrorTopic",
            topic_arn=input_internal_error_topic_arn,
        )

        return settings_bucket, internal_error_topic, input_timestream_database_arn, input_timestream_database_name

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
            "ExtractMetricsLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=AWSNaming.IAMRole(
                self, CDKResourceNames.IAMROLE_EXTRACT_METRICS_LAMBDA
            ),
        )

        extract_metrics_lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        tooling_acc_inline_policy = iam.Policy(
            self,
            "ToolingAccPermissions",
            policy_name=AWSNaming.IAMPolicy(self, "tooling-acc-permissions"),
        )
        extract_metrics_lambda_role.attach_inline_policy(tooling_acc_inline_policy)

        tooling_acc_inline_policy.add_statements(
            # to be able to read settings
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[f"{settings_bucket.bucket_arn}/*"],
            )
        )
        tooling_acc_inline_policy.add_statements(
            # to be able to throw internal Salmon errors
            iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                resources=[internal_error_topic.topic_arn],
            )
        )
        tooling_acc_inline_policy.add_statements(
            # to be able to write extracted metrics to Timestream DB
            iam.PolicyStatement(
                actions=["timestream:*"],
                effect=iam.Effect.ALLOW,
                resources=[timestream_database_arn],
            )
        )

        monitored_assume_inline_policy = iam.Policy(
            self,
            "MonitoredAccAssumePermissions",
            policy_name=AWSNaming.IAMPolicy(self, "monitored-acc-assume-permissions"),
        )
        extract_metrics_lambda_role.attach_inline_policy(monitored_assume_inline_policy)

        monitored_account_ids = self.settings.get_monitored_account_ids()
        extr_metr_role_name = AWSNaming.IAMRole(
            self, CDKResourceNames.IAMROLE_MONITORED_ACC_EXTRACT_METRICS
        )
        for monitored_account_id in monitored_account_ids:
            mon_acc_extr_metr_role_arn = AWSNaming.Arn_IAMRole(
                self, monitored_account_id, extr_metr_role_name
            )
            monitored_assume_inline_policy.add_statements(
                # to be able to assume role in monitored account to extract metrics
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    effect=iam.Effect.ALLOW,
                    resources=[mon_acc_extr_metr_role_arn],
                )
            )

        current_region = Stack.of(self).region
        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            id="lambda-powertools",
            layer_version_arn=AWS_Common_Resources.get_Lambda_Powertools_Layer_Arn(current_region)
        )

        extract_metrics_lambda_path = os.path.join("../src/")
        extract_metrics_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsLambda",
            function_name=AWSNaming.LambdaFunction(self, "extract-metrics"),
            code=lambda_.Code.from_asset(
                extract_metrics_lambda_path,
                exclude=CDKDeployExclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_extract_metrics.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_PATH": f"s3://{settings_bucket.bucket_name}/settings/",
                "IAMROLE_MONITORED_ACC_EXTRACT_METRICS": extr_metr_role_name,
            },
            role=extract_metrics_lambda_role,
            layers=[powertools_layer],
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        extract_metrics_orch_lambda_path = os.path.join("../src/")
        extract_metrics_orch_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsOrchLambda",
            function_name=AWSNaming.LambdaFunction(self, "extract-metrics-orch"),
            code=lambda_.Code.from_asset(
                extract_metrics_orch_lambda_path,
                exclude=CDKDeployExclusions.LAMBDA_ASSET_EXCLUSIONS,
                ignore_mode=IgnoreMode.GIT,
            ),
            handler="lambda_extract_metrics_orch.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_PATH": f"s3://{settings_bucket.bucket_name}/settings/",
                "IAMROLE_MONITORED_ACC_EXTRACT_METRICS": extr_metr_role_name,
            },
            role=extract_metrics_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        return extract_metrics_orch_lambda, extract_metrics_lambda

    def create_metrics_tables(self, timestream_database_name):
        """
        Creates Timestream tables for storing metrics for each service.

        Parameters:
            timestream_database_arn (str): The ARN of the Timestream database for storing metrics.
        """
        metric_table_names = CDKResourceNames.TIMESTREAM_TABLE_METRICS
        services = metric_table_names.keys()

        retention_properties_property = timestream.CfnTable.RetentionPropertiesProperty(
            magnetic_store_retention_period_in_days=TimestreamRetention.MagneticStoreRetentionPeriodInDays,
            memory_store_retention_period_in_hours=TimestreamRetention.MemoryStoreRetentionPeriodInHours,
        )

        for service in services:
            timestream.CfnTable(
                self,
                f"MetricsTable{service}",
                database_name=timestream_database_name,
                retention_properties=retention_properties_property,
                table_name=AWSNaming.TimestreamTable(self, metric_table_names[service]),
            )

