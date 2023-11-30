from .impl import GlueEventMapper, StepFunctionsEventMapper, EventParsingException
from ..settings import Settings


class AwsEventMapper:
    def __init__(self, settings: Settings):
        self.settings = settings

        self.event_map = {
            "aws.glue": GlueEventMapper(settings),
            "aws.states": StepFunctionsEventMapper(settings),
        }

    def to_notification_messages(self, event):
        event_source = event["source"]

        if event_source not in self.event_map:
            raise EventParsingException(f"No parsing logic for source {event_source}.")

        target_mapper = self.event_map[event_source]

        return target_mapper.to_notification_messages(event)
