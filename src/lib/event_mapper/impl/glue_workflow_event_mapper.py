from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings

from ...core.constants import EventResult
from ...aws.glue_manager import GlueManager

# Workflows are not yet supported as EventBridge Events by AWS, so leaving it like that for now
class GlueWorkflowEventMapper(GeneralAwsEventMapper):

    def __init__(
        self,
        event: dict,
        settings: Settings
    ):
        super().__init__(event, settings)
        
        details = event["detail"]
        self.monitored_env_name = settings.get_monitored_environment_name(details["origin_account"], details["origin_region"])

    def get_resource_name(self):
        return self.event["detail"]["workflowName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        return self.event["detail"]["event_result"]

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        rows.append(
            super().create_table_row(["Workflow Name", self.event["detail"]["workflowName"]])
        )
        return message_body
