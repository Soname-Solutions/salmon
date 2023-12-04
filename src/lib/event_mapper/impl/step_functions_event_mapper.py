from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from datetime import datetime


class StepFunctionsEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        arn = event["detail"]["stateMachineArn"]
        return arn.split("stateMachine:")[1]

    @staticmethod
    def __timestamp_to_datetime(timestamp: int) -> str:
        """Formats integer datetime from the event to the ISO formatted datetime string

        Args:
            timestamp (int): Timestamp with milliseconds

        Returns:
            str: ISO formatted datetime
        """
        return datetime.fromtimestamp(timestamp / 1e3).isoformat()

    def get_message_body(self, event):
        message_body = []
        table = {}
        rows = []
        table["table"] = {}
        table["table"]["rows"] = rows
        message_body.append(table)

        style = (
            "error" if event["detail"]["status"] in ["FAILED", "TIMED_OUT"] else None
        )

        rows.append(super().create_table_row(["AWS Account", event["account"]]))
        rows.append(super().create_table_row(["AWS Region", event["region"]]))
        rows.append(super().create_table_row(["Time", event["time"]]))
        rows.append(
            super().create_table_row(
                ["State Machine Name", self.get_resource_name(event)]
            )
        )
        rows.append(
            super().create_table_row(["Execution Name", event["detail"]["name"]])
        )
        rows.append(
            super().create_table_row(["Status", event["detail"]["status"]], style)
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
