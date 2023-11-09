from aws_cdk import (
    Stack,
    Tags,
    aws_iam as iam
)
from constructs import Construct
import json

class InfraMonitoredStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)
        
        super().__init__(scope, construct_id, **kwargs)
        
        #General settings config
        general_settings_file_path = "../config/settings/general.json"
        with open(general_settings_file_path) as f:
            try:
                general_config = json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise json.decoder.JSONDecodeError(
                f"Error parsing JSON file {general_settings_file_path}", e.doc, e.pos
            )
        
        
        #IAM role and policies for sending events
        cross_account_bus_role = iam.Role(
            self,
            "salmonCrossAccountPutEventsRole",
            role_name=f"role-{project_name}-cross-account-put-events-{stage_name}",
            description="Role assumed by EventBridge to put events to the centralized bus",
            assumed_by=iam.ServicePrincipal('events.amazonaws.com')
        )
        
        
        tooling_account_id = general_config["tooling_account"]["AccountId"]
        tooling_account_region = general_config["tooling_account"]["Region"]
        cross_account_event_bus_name = f"eventbus-{project_name}-notification-{stage_name}"
        cross_account_bus_role.add_to_policy(
            iam.PolicyStatement(
                actions=["events:PutEvents"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:events:{tooling_account_region}:{tooling_account_id}:event-bus/{cross_account_event_bus_name}"]
            )
        )
        cross_account_bus_role.grant_assume_role(iam.AccountPrincipal(tooling_account_id))
        
        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)