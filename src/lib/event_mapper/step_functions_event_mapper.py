from datetime import datetime
from lib.event_mapper.general_aws_event_mapper import (
    GeneralAwsEventMapper,
    ExecutionInfoUrlMixin,
)
from lib.core.constants import EventResult
from lib.core import datetime_utils
from lib.aws.step_functions_manager import StepFunctionsManager


class StepFunctionsEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        arn = self.event["detail"]["stateMachineArn"]
        return arn.split("stateMachine:")[1]

    def get_resource_state(self):
        return self.event["detail"]["status"]

    def get_event_result(self):
        if self.get_resource_state() in StepFunctionsManager.STATES_FAILURE:
            return EventResult.FAILURE
        elif self.get_resource_state() in StepFunctionsManager.STATES_SUCCESS:
            return EventResult.SUCCESS
        else:
            return EventResult.INFO

    def get_execution_info_url(self, resource_name: str):
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
            account_id=self.event["account"],
            run_id=self.event["detail"]["name"],
        )

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["State Machine Name", self.get_resource_name()])
        )
        rows.append(
            super().create_table_row(["Status", self.get_resource_state()], style)
        )
        rows.append(
            super().create_table_row(
                [
                    "Start Date",
                    datetime_utils.epoch_milliseconds_to_iso_date_string(
                        self.event["detail"]["startDate"]
                    ),
                ]
            )
        )
        rows.append(
            super().create_table_row(
                [
                    "Stop Date",
                    datetime_utils.epoch_milliseconds_to_iso_date_string(
                        self.event["detail"]["stopDate"]
                    ),
                ]
            )
        )

        link_url = self.get_execution_info_url(self.get_resource_name())
        rows.append(
            super().create_table_row(
                [
                    "Execution Info",
                    f"<a href='{link_url}'>{self.event['detail']['name']}</a>",
                ]
            )
        )

        return message_body
