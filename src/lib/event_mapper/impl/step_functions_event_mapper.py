from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from datetime import datetime
from ...core.constants import EventResult
from ...aws.step_functions_manager import StepFunctionsManager


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

    def get_execution_info_url(self):
        return (
            f"https://{self.event['region']}.console.aws.amazon.com/states/home?region={self.event['region']}#/v2/executions/details/"
            f"arn:aws:states:{self.event['region']}:{self.event['account']}:execution:{self.get_resource_name()}:{self.event['detail']['name']}"
        )

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

    def get_message_body(self):
        message_body, rows = super().create_message_body_with_common_rows()

        style = super().get_row_style()

        rows.append(
            super().create_table_row(["State Machine Name", self.get_resource_name()])
        )
        rows.append(
            super().create_table_row(["Execution Name", self.event["detail"]["name"]])
        )
        rows.append(
            super().create_table_row(["Status", self.get_resource_state()], style)
        )
        rows.append(
            super().create_table_row(
                [
                    "Start Date",
                    self.__timestamp_to_datetime(self.event["detail"]["startDate"]),
                ]
            )
        )
        rows.append(
            super().create_table_row(
                [
                    "Stop Date",
                    self.__timestamp_to_datetime(self.event["detail"]["stopDate"]),
                ]
            )
        )

        return message_body
