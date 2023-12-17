from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct

from lib.aws.aws_naming import AWSNaming
from lib.core.constants import CDKResourceNames
from lib.settings import Settings


class InfraMonitoredStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)
        self.settings: Settings = kwargs.pop("settings", None)

        (
            self.tooling_account_id,
            self.tooling_account_region,
        ) = self.settings.get_tooling_account_props()

        super().__init__(scope, construct_id, **kwargs)

        (
            cross_account_bus_role,
            cross_account_event_bus_arn,
        ) = self.create_cross_account_event_bus_role()

        event_rules = self.create_event_rules(
            cross_account_bus_role, cross_account_event_bus_arn
        )

        metrics_extract_role = self.create_metrics_extract_iam_role()

    def create_cross_account_event_bus_role(self):
        # General settings config
        cross_account_bus_role = iam.Role(
            self,
            "MonitoredAccPutEventsRole",
            role_name=AWSNaming.IAMRole(
                self, CDKResourceNames.IAMROLE_MONITORED_ACC_PUT_EVENTS
            ),
            description="Role assumed by EventBridge to put events to the centralized bus",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )

        cross_account_event_bus_name = AWSNaming.EventBus(
            self, CDKResourceNames.EVENTBUS_ALERTING
        )

        cross_account_event_bus_arn = f"arn:aws:events:{self.tooling_account_region}:{self.tooling_account_id}:event-bus/{cross_account_event_bus_name}"
        cross_account_bus_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[cross_account_event_bus_arn],
            )
        )
        cross_account_bus_role.grant_assume_role(
            iam.AccountPrincipal(self.tooling_account_id)
        )

        return cross_account_bus_role, cross_account_event_bus_arn

    def create_event_rules(self, cross_account_bus_role, cross_account_event_bus_arn):
        # EventBridge Glue rule
        glue_alerting_event_rule = events.Rule(
            self,
            "salmonGlueAlertingEventRule",
            rule_name=AWSNaming.EventBusRule(self, "glue"),
            event_pattern=events.EventPattern(source=["aws.glue"]),
        )

        # EventBridge Step Functions rule
        step_functions_alerting_event_rule = events.Rule(
            self,
            "salmonStepFunctionsAlertingEventRule",
            rule_name=AWSNaming.EventBusRule(self, "step-functions"),
            event_pattern=events.EventPattern(source=["aws.states"]),
        )

        rule_target = targets.EventBus(
            event_bus=events.EventBus.from_event_bus_arn(
                self, "CrossAccountEventBus", cross_account_event_bus_arn
            ),
            role=cross_account_bus_role,
        )

        glue_alerting_event_rule.add_target(rule_target)
        step_functions_alerting_event_rule.add_target(rule_target)

        return [glue_alerting_event_rule, step_functions_alerting_event_rule]

    def create_metrics_extract_iam_role(self):
        """
        Creates an IAM Role allowing Tooling Account's MetricsExtractor Lambda get required data from Monitored account
        """
        # todo: do we need multiple arns (lambdas)?
        # todo: how to get tooling extract lambda role -> through AWSNaming?
        tooling_extract_lambda_role_name = AWSNaming.IAMRole(
            self, CDKResourceNames.IAMROLE_EXTRACT_METRICS_LAMBDA
        )
        principal_arn = AWSNaming.Arn_IAMRole(
            self, self.tooling_account_id, tooling_extract_lambda_role_name
        )

        # todo rename
        cross_account_iam_role_extract_metrics = iam.Role(
            self,
            "MonitoredAccExtractMetricsRole",
            role_name=AWSNaming.IAMRole(
                self, CDKResourceNames.IAMROLE_MONITORED_ACC_EXTRACT_METRICS
            ),
            assumed_by=iam.ArnPrincipal(principal_arn),
        )

        # Glue Policy
        glue_policy_statement = iam.PolicyStatement(
            actions=[
                "glue:ListJobs",
                "glue:ListWorkflows",
                "glue:GetJob",
                "glue:GetJobs",
                "glue:GetJobRun",
                "glue:GetJobRuns",
            ],
            resources=["*"],
            effect=iam.Effect.ALLOW,
        )
        glue_inline_policy = iam.Policy(
            self, "glue-extract", policy_name=AWSNaming.IAMPolicy(self, "glue-extract")
        )
        glue_inline_policy.add_statements(glue_policy_statement)

        # Lambda Policy (extract via CloudWatch logs)
        lambda_policy_statement = iam.PolicyStatement(
            actions=[
                "lambda:ListFunctions",
                "logs:GetQueryResults",
                "logs:StartQuery",
                "logs:StopQuery",
            ],
            resources=["*"],
            effect=iam.Effect.ALLOW,
        )
        lambda_inline_policy = iam.Policy(
            self,
            "lambda-extract",
            policy_name=AWSNaming.IAMPolicy(self, "lambda-extract"),
        )
        lambda_inline_policy.add_statements(lambda_policy_statement)

        # Step Functions Policy
        step_functions_policy_statement = iam.PolicyStatement(
            actions=[
                "states:ListStateMachines",
            ],
            resources=["*"],
            effect=iam.Effect.ALLOW,
        )
        step_functions_inline_policy = iam.Policy(
            self,
            "states-extract",
            policy_name=AWSNaming.IAMPolicy(self, "states-extract"),
        )
        step_functions_inline_policy.add_statements(step_functions_policy_statement)

        cross_account_iam_role_extract_metrics.attach_inline_policy(glue_inline_policy)
        cross_account_iam_role_extract_metrics.attach_inline_policy(
            lambda_inline_policy
        )
        cross_account_iam_role_extract_metrics.attach_inline_policy(
            step_functions_inline_policy
        )

        return cross_account_iam_role_extract_metrics
