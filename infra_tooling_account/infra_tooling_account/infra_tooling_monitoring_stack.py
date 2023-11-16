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


class InfraToolingMonitoringStack(Stack):
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

        extract_metrics_orch_lambda, extract_metrics_lambda = self.create_extract_metrics_lambdas(
            settings_bucket=settings_bucket,            
            internal_error_topic=internal_error_topic,
            timestream_database_arn=input_timestream_database_arn
        )        

    #     extract-metrics_bus, extract-metrics_lambda_event_rule = self.create_event_bus()

    #     extract-metrics_lambda = self.create_extract-metrics_lambda(
    #         settings_bucket=settings_bucket,
    #         notification_queue=notification_queue,
    #         internal_error_topic=internal_error_topic,
    #         timestream_database_arn=input_timestream_database_arn,
    #         extract-metrics_lambda_event_rule=extract-metrics_lambda_event_rule,
    #     )

    # def create_event_bus(self):
    #     extract-metrics_bus = events.EventBus(
    #         self,
    #         "salmonMonitoringBus",
    #         event_bus_name=f"eventbus-{self.project_name}-extract-metrics-{self.stage_name}",
    #     )

    #     # EventBridge bus resource policy
    #     # TODO: reuse existing settings reader
    #     general_settings_file_path = "../config/settings/general.json"
    #     with open(general_settings_file_path) as f:
    #         try:
    #             general_config = json.load(f)
    #         except json.decoder.JSONDecodeError as e:
    #             raise json.decoder.JSONDecodeError(
    #                 f"Error parsing JSON file {general_settings_file_path}",
    #                 e.doc,
    #                 e.pos,
    #             )

    #     monitored_account_ids = set(
    #         [
    #             account["account_id"]
    #             for account in general_config["monitored_environments"]
    #         ]
    #     )
    #     monitored_principals = [
    #         iam.AccountPrincipal(account_id) for account_id in monitored_account_ids
    #     ]

    #     extract-metrics_bus.add_to_resource_policy(
    #         iam.PolicyStatement(
    #             sid=f"policy-{self.project_name}-AllowMonitoredAccountsPutEvents-{self.stage_name}",
    #             actions=["events:PutEvents"],
    #             effect=iam.Effect.ALLOW,
    #             resources=[extract-metrics_bus.event_bus_arn],
    #             principals=monitored_principals,
    #         )
    #     )

    #     extract-metrics_lambda_event_rule = events.Rule(
    #         self,
    #         "salmonMonitoringLambdaEventRule",
    #         rule_name=f"eventbusrule-{self.project_name}-extract-metrics-lambda-{self.stage_name}",
    #         event_bus=extract-metrics_bus,
    #         event_pattern=events.EventPattern(source=events.Match.prefix("aws")),
    #     )

    #     return extract-metrics_bus, extract-metrics_lambda_event_rule

    def create_extract_metrics_lambdas(
        self,
        settings_bucket,
        internal_error_topic,
        timestream_database_arn
    ):
        extract_metrics_lambda_role = iam.Role(
            self,
            "extract-metricsLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=f"role-{self.project_name}-extract-metrics-lambda-{self.stage_name}",
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

        extract_metrics_lambda_path = os.path.join("../src/", "lambda/extract-metrics-lambda")
        extract_metrics_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsLambda",
            function_name=f"lambda-{self.project_name}-extract-metrics-{self.stage_name}",
            code=lambda_.Code.from_asset(extract_metrics_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_BUCKET_NAME": settings_bucket.bucket_name
            },
            role=extract_metrics_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )

        extract_metrics_orch_lambda_path = os.path.join("../src/", "lambda/extract-metrics-orch-lambda")
        extract_metrics_orch_lambda = lambda_.Function(
            self,
            "salmonExtractMetricsOrchLambda",
            function_name=f"lambda-{self.project_name}-extract-metrics-orch-{self.stage_name}",
            code=lambda_.Code.from_asset(extract_metrics_orch_lambda_path),
            handler="index.lambda_handler",
            timeout=Duration.seconds(900),
            runtime=lambda_.Runtime.PYTHON_3_11,
            environment={
                "SETTINGS_S3_BUCKET_NAME": settings_bucket.bucket_name
            },
            role=extract_metrics_lambda_role,
            retry_attempts=2,
            dead_letter_topic=internal_error_topic,
        )        

        return extract_metrics_orch_lambda, extract_metrics_lambda
