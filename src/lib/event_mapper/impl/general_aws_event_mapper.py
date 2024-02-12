from abc import ABC, abstractmethod
from ...core.constants import EventResult
from ..resource_type_resolver import ResourceTypeResolver
from lib.settings import Settings


class EventParsingException(Exception):
    pass


class GeneralAwsEventMapper(ABC):
    """Abstract class containing common logic to map AWS events to notification messages.

    Attributes:
        settings(Settings): Settings object

    Methods:
        to_notification_messages(dict): maps AWS event object to a list of notification message objects
    """

    def __init__(
        self,
        event: dict,
        settings: Settings
    ):
        self.event = event
        self.monitored_env_name = settings.get_monitored_environment_name(event["account"], event["region"])

    @abstractmethod
    def get_resource_name(self, event: dict) -> str:
        """Returns name of the AWS resource the given event belongs to (job/stateMachine/function etc.)

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_event_result(self, event: dict) -> str:
        """Returns the result of the occurred event

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_resource_state(self, event: dict) -> str:
        """Returns the state of the resource according to the event

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_message_body(self, event: dict) -> list[dict]:
        """Returns composed message body for the given AWS event

        Args:
            event (dict): Event object
        """
        pass

    def __get_message_subject(self, event: dict) -> str:
        """Return message subject based on the event

        Args:
            event (dict): Event object

        Returns:
            str: Message subject
        """
        resource_name = self.get_resource_name(event)
        resource_state = self.get_resource_state(event)
        resource_type = ResourceTypeResolver.resolve(event)        
        return f"{self.monitored_env_name}: {resource_state} - {resource_type} : {resource_name}"

    def create_message_body_with_common_rows(self, event) -> tuple[list, list]:
        message_body = []
        table = {}
        rows = []
        table["table"] = {}
        table["table"]["rows"] = rows
        message_body.append(table)

        # todo: when completing task for event -> self.event, also override this method for glue workflows
        rows.append(self.create_table_row(["AWS Account", event["account"]]))
        rows.append(self.create_table_row(["AWS Region", event["region"]]))
        rows.append(self.create_table_row(["Time", event["time"]]))
        rows.append(self.create_table_row(["Event Type", event["detail-type"]]))

        return message_body, rows

    def get_row_style(self, event) -> str:
        return "error" if self.get_event_result(event) == EventResult.FAILURE else None

    def create_table_row(self, values: list, style: str = None) -> dict:
        """Returns prepared table row for given values and style

        Args:
            values (list): List of values to put in columns
            style (str, optional): Style to apply to the row. Defaults to None.

        Returns:
            dict: Row object
        """
        row = {"values": values}
        if style is not None:
            row["style"] = style
        return row

    def to_message(self, event: dict) -> dict:
        """Maps AWS event object to a message object structure

        Args:
            event (dict): Event object

        Returns:
            dict: Message to be sent as a notification
        """
        message = {
            "message_subject": self.__get_message_subject(event),
            "message_body": self.get_message_body(event),
        }

        return message
