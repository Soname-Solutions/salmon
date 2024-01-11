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

    def __get_event_mapper(self, event: dict) -> GeneralAwsEventMapper:
        """Retrieves event mapper for a provided event.

        Args:
            event (dict): Event to process

        Raises:
            EventParsingException: If no mapper is found for the event.

        Returns:
            GeneralAwsEventMapper: Event mapper with service specific logic.
        """
        event_source = event["source"]

        if event_source not in self.event_map:
            raise EventParsingException(f"No parsing logic for source {event_source}.")

        return self.event_map[event_source]

    def to_resource_name(self, event: dict) -> str:
        """Retrieves the name of the AWS resource the event is related to.

        Args:
            event (dict): Event to analyze.

        Returns:
            str: AWS resource name.
        """
        target_mapper = self.__get_event_mapper(event)
        return target_mapper.get_resource_name(event)

    def to_service_name(self, event: dict) -> str:
        """Retrieves the name of the AWS service the event is related to.

        Args:
            event (dict): Event to analyze.

        Returns:
            str: AWS service name.
        """
        target_mapper = self.__get_event_mapper(event)
        return target_mapper.get_service_name()

    def to_event_status(self, event: dict) -> str:
        """Retrieves the status of the event.

        Args:
            event (dict): Event to analyze.

        Returns:
            str: AWS service name.
        """
        target_mapper = self.__get_event_mapper(event)
        return target_mapper.get_event_status(event)

    def to_event_severity(self, event: dict) -> str:
        """Determines the severity of the event.

        Args:
            event (dict): Event to analyze.

        Returns:
            str: Event severity.
        """
        target_mapper = self.__get_event_mapper(event)
        return target_mapper.get_event_severity(event)

    def to_notification_messages(self, event: dict) -> list[dict]:
        """Maps AWS event object to a list of notification message objects

        Args:
            event (dict): Event object

        Raises:
            EventParsingException: In case of error during mapping process

        Returns:
            list[dict]: List of message objects
        """
        target_mapper = self.__get_event_mapper(event)

        return target_mapper.to_notification_messages(event)
