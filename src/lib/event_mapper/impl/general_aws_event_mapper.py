from abc import ABC, abstractmethod
from ...core.constants import NotificationType
from ...settings import Settings


class EventParsingException(Exception):
    pass


class GeneralAwsEventMapper(ABC):
    """Abstract class containing common logic to map AWS events to notification messages"""

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def get_resource_name(self, event: dict):
        """Returns name of the AWS resource the given event belongs to (job/stateMachine/function etc.)

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_message_body(self, event: dict):
        """Returns composed message body for the given AWS event

        Args:
            event (dict): Event object
        """
        pass

    def __get_delivery_options(self, resource_name: str) -> list[dict]:
        """Returns delivery options section for the given resource name based on settings config.

        Args:
            resource_name (str): Name of the AWS resourcce

        Returns:
            list[dict]: List of delivery options including recipient and delivery method
        """
        delivery_options = []
        recipients = {}
        monitoring_groups = self.settings.get_monitoring_groups([resource_name])
        recipients_settings = self.settings.get_recipients(
            monitoring_groups, NotificationType.ALERT
        )

        for recipient_setting in recipients_settings:
            delivery_method = recipient_setting["delivery_method"]
            recipient = recipient_setting["recipient"]

            if delivery_method not in recipients:
                recipients[delivery_method] = []

            recipients[delivery_method].append(recipient)

        for delivery_method, recipients_array in recipients.items():
            delivery_option = {
                "delivery_method": delivery_method,
                "recipients": recipients_array,
                "sender_email": self.settings.get_sender_email(delivery_method),
            }
            delivery_options.append(delivery_option)

        return delivery_options

    def __to_notification_messages(
        self, delivery_options: list[dict], message: dict
    ) -> list[dict]:
        """Maps delivery options and given message to the notification messages array

        Args:
            delivery_options (list[dict]): List of delivery options
            message (dict): Message to be sent

        Returns:
            list[dict]: List of notification messages
        """
        notification_messages = []

        for delivery_option in delivery_options:
            notification_message = {
                "delivery_options": delivery_option,
                "message": message,
            }
            notification_messages.append(notification_message)

        return notification_messages

    def __get_message_subject(self, event: dict) -> str:
        """Return message subject based on the event

        Args:
            event (dict): Event object

        Returns:
            str: Message subject
        """
        monitored_env_name = self.settings.get_monitored_environment_name(
            event["account"], event["region"]
        )
        event_message = event["detail-type"]
        return f"{monitored_env_name}: {event_message}"

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

    def to_notification_messages(self, event: dict) -> list[dict]:
        """Maps AWS event object to a list of notification message objects

        Args:
            event (dict): Event object

        Returns:
            list[dict]: List of message objects
        """
        resource_name = self.get_resource_name(event)
        delivery_options = self.__get_delivery_options(resource_name)

        message = {
            "message_subject": self.__get_message_subject(event),
            "message_body": self.get_message_body(event),
        }

        return self.__to_notification_messages(delivery_options, message)
