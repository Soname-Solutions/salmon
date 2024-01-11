from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings


# Workflows are not yet supported as EventBridge Events by AWS, so leaving it like that for now
class GlueWorkflowEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        return event["detail"]["workflowName"]

    def get_resource_state(self, event):
        return event["detail"]["state"]

    def get_event_severity(self, event):
        return "Unknown"

    def get_message_body(self, event):
        message_body, rows = super().create_message_body_with_common_rows(event)

        rows.append(
            super().create_table_row(["Workflow Name", event["detail"]["jobName"]])
        )
        return message_body
