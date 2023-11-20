from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct
import json


class InfraMonitoredStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        (
            cross_account_bus_role,
            cross_account_event_bus_arn,
        ) = self.create_cross_account_event_bus_role()

        event_rules = self.create_event_rules(
            cross_account_bus_role, cross_account_event_bus_arn
        )

    def create_cross_account_event_bus_role(self):
        # General settings config
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

        cross_account_bus_role = iam.Role(
            self,
            "salmonCrossAccountPutEventsRole",
            role_name=f"role-{self.project_name}-cross-account-put-events-{self.stage_name}",
            description="Role assumed by EventBridge to put events to the centralized bus",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )

        tooling_account_id = general_config["tooling_environment"]["account_id"]
        tooling_account_region = general_config["tooling_environment"]["region"]
        cross_account_event_bus_name = (
            f"eventbus-{self.project_name}-alerting-{self.stage_name}"
        )
        cross_account_event_bus_arn = f"arn:aws:events:{tooling_account_region}:{tooling_account_id}:event-bus/{cross_account_event_bus_name}"
        cross_account_bus_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[cross_account_event_bus_arn],
            )
        )
        cross_account_bus_role.grant_assume_role(
            iam.AccountPrincipal(tooling_account_id)
        )

        return cross_account_bus_role, cross_account_event_bus_arn

    def create_event_rules(self, cross_account_bus_role, cross_account_event_bus_arn):
        # EventBridge Glue rule
        glue_alerting_event_rule = events.Rule(
            self,
            "salmonGlueAlertingEventRule",
            rule_name=f"eventbusrule-{self.project_name}-glue-{self.stage_name}",
            event_pattern=events.EventPattern(source=["aws.glue"]),
        )

        # EventBridge Step Functions rule
        step_functions_alerting_event_rule = events.Rule(
            self,
            "salmonStepFunctionsAlertingEventRule",
            rule_name=f"eventbusrule-{self.project_name}-step-functions-{self.stage_name}",
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
