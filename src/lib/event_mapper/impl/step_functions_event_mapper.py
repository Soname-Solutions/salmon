from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings


class StepFunctionsEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        return event["detail"]["stateMachineArn"]

    def get_message(self, event):
        message = {}
        message["message_subject"] = event["detail-type"]
        message["message_body"] = "Step Function happened"  # TODO: implement

        return message
