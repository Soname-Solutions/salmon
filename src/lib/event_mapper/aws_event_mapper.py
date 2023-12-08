from .impl import (
    GeneralAwsEventMapper,
    GlueEventMapper,
    StepFunctionsEventMapper,
    EventParsingException,
)
from ..settings import Settings


class AwsEventMapper:
    """Class designed to map AWS events to notification messages"""

    def __init__(self, settings: Settings):
        self.settings = settings

        self.event_map = {
            "aws.glue": GlueEventMapper(settings),
            "aws.states": StepFunctionsEventMapper(settings),
        }

    def to_notification_messages(self, event: dict) -> list[dict]:
        """Maps AWS event object to a list of notification message objects

        Args:
            event (dict): Event object

        Raises:
            EventParsingException: In case of error during mapping process

        Returns:
            list[dict]: List of message objects
        """
        event_source = event["source"]

        if event_source not in self.event_map:
            raise EventParsingException(f"No parsing logic for source {event_source}.")

        target_mapper: GeneralAwsEventMapper = self.event_map[event_source]

        return target_mapper.to_notification_messages(event)
