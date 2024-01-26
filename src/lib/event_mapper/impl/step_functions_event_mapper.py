from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from datetime import datetime
from ...core.constants import EventResult
from ...aws.step_functions_manager import StepFunctionsManager


class StepFunctionsEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self, event):
        arn = event["detail"]["stateMachineArn"]
        return arn.split("stateMachine:")[1]

    def get_resource_state(self, event):
        return event["detail"]["status"]

    def get_event_result(self, event):
        if self.get_resource_state(event) in StepFunctionsManager.STATES_FAILURE:
            return EventResult.FAILURE
        if self.get_resource_state(event) in StepFunctionsManager.STATES_SUCCESS:
            return EventResult.SUCCESS
        return EventResult.INFO

    @staticmethod
    def __timestamp_to_datetime(timestamp: int) -> str:
        """Formats integer datetime from the event to the ISO formatted datetime string

        Args:
            timestamp (int): Timestamp with milliseconds

        Returns:
            str: ISO formatted datetime
        """
        if timestamp is not None:
            return datetime.fromtimestamp(timestamp / 1e3).isoformat()
        return None

    def get_message_body(self, event):
        message_body, rows = super().create_message_body_with_common_rows(event)

        style = super().get_row_style(event)

        rows.append(
            super().create_table_row(
                ["State Machine Name", self.get_resource_name(event)]
            )
        )
        rows.append(
            super().create_table_row(["Execution Name", event["detail"]["name"]])
        )
        rows.append(
            super().create_table_row(["Status", self.get_resource_state(event)], style)
        )
        rows.append(
            super().create_table_row(
                [
                    "Start Date",
                    self.__timestamp_to_datetime(event["detail"]["startDate"]),
                ]
            )
        )
        rows.append(
            super().create_table_row(
                ["Stop Date", self.__timestamp_to_datetime(event["detail"]["stopDate"])]
            )
        )

        return message_body
