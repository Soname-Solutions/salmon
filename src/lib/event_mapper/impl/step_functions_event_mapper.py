from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
import boto3


class StepFunctionsEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.client = boto3.client("stepfunctions")

    def get_resource_name(self, event):
        state_machine = self.client.describe_state_machine(
            stateMachineArn=event["detail"]["stateMachineArn"]
        )
        return state_machine["name"]

    def get_message(self, event):
        message = {}
        message["message_subject"] = event["detail-type"]
        message["message_body"] = "Step Function happened"  # TODO: implement

        return message
