from .general_aws_event_mapper import GeneralAwsEventMapper
from .general_aws_event_mapper import ExecutionInfoUrlMixin
from ...settings import Settings

from ...core.constants import EventResult
from ...aws.lambda_manager import LambdaManager


# Lambda Functions are not yet supported as EventBridge Events by AWS, so leaving it like that for now
class LambdaFunctionsEventMapper(GeneralAwsEventMapper):
    def __init__(self, resource_type: str, event: dict, settings: Settings):
        super().__init__(resource_type, event, settings)

        details = event["detail"]
        self.monitored_env_name = settings.get_monitored_environment_name(
            details["origin_account"], details["origin_region"]
        )

    def get_resource_name(self):
        return self.event["detail"]["lambdaName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        return self.event["detail"]["event_result"]

    def get_execution_info_url(self, resource_name: str):
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["detail"]["origin_region"],
            resource_name=resource_name,
        )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(
                ["Function Name", self.event["detail"]["lambdaName"]]
            )
        )

        # Get resource state and include in the Alert if available
        resource_state = self.get_resource_state()
        if resource_state:
            rows.append(super().create_table_row(["State", resource_state], style))

        # Get link URL for log events
        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                [
                    "Log Events",
                    f"<a href='{link_url}'>Link to AWS CloudWatch Log Group</a>",
                ]
            )
        )

        # Get Lambda Message
        rows.append(
            super().create_table_row(["Message", self.event["detail"]["message"]])
        )

        # Get Lambda Request ID and include in the Alert if available
        request_id = self.event["detail"]["request_id"]
        if request_id:
            rows.append(super().create_table_row(["Request ID", request_id]))

        return message_body
