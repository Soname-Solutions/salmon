from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings


class GlueEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        return event["detail"]["jobName"]

    def get_message(self, event):
        message = {}
        message["message_subject"] = event["detail-type"]
        message["message_body"] = "Glue Job happened"  # TODO: implement

        return message
