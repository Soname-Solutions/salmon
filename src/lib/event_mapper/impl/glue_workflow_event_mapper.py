from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings

from ...core.constants import EventResult
from ...aws.glue_manager import GlueManager

# Workflows are not yet supported as EventBridge Events by AWS, so leaving it like that for now
class GlueWorkflowEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self, event):
        return event["detail"]["workflowName"]

    def get_resource_state(self, event):
        return event["detail"]["state"]

    def get_event_result(self, event):
        return event["detail"]["event_result"]

    def get_message_body(self, event):
        message_body, rows = super().create_message_body_with_common_rows(event)

        rows.append(
            super().create_table_row(["Workflow Name", event["detail"]["workflowName"]])
        )
        return message_body
