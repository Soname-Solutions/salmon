from abc import ABC, abstractmethod
from ...core.constants import NotificationType
from ...settings import Settings


class EventParsingException(Exception):
    pass


class GeneralAwsEventMapper(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def get_resource_name(self, event):
        pass

    @abstractmethod
    def get_message_body(self, event):
        pass

    def __get_delivery_options(self, resource_name):
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

    def __to_notification_messages(self, delivery_options, message):
        notification_messages = []

        for delivery_option in delivery_options:
            notification_message = {
                "delivery_options": delivery_option,
                "message": message,
            }
            notification_messages.append(notification_message)

        return notification_messages

    def __get_message_subject(self, event):
        monitored_env_name = self.settings.get_monitored_environment_name(
            event["account"], event["region"]
        )
        event_message = event["detail-type"]
        return f"{monitored_env_name}: {event_message}"

    def create_table_row(self, values, style=None):
        row = {"values": values}
        if style is not None:
            row["style"] = style
        return row

    def to_notification_messages(self, event):
        resource_name = self.get_resource_name(event)
        delivery_options = self.__get_delivery_options(resource_name)

        message = {
            "message_subject": self.__get_message_subject(event),
            "message_body": self.get_message_body(event),
        }

        return self.__to_notification_messages(delivery_options, message)
