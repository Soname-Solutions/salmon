from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.aws.emr_manager import EMRManager


class EMRServerlessEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["applicationName"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        if self.get_resource_state() in EMRManager.STATES_FAILURE:
            return EventResult.FAILURE
        elif self.get_resource_state() in EMRManager.STATES_SUCCESS:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def get_execution_info_url(self, resource_name: str):
        return ""

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["Name", self.event["detail"]["applicationName"]])
        )
        rows.append(
            super().create_table_row(["State", self.get_resource_state()], style)
        )
        return message_body
