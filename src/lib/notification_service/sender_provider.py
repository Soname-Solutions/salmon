from lib.notification_service.sender import (
    AwsSesSender,
    AwsSnsSender,
    SmtpSender,
)
from .messages import Message
from typing import List

from lib.core.constants import DeliveryMethodTypes
from lib.settings.settings_classes import DeliveryMethod


class SenderProvider:
    """Sender factory."""

    def __init__(self):
        self._senders = {}

    def register_sender(self, delivery_method_type: str, sender):
        self._senders[delivery_method_type] = sender

    def get(
        self, delivery_method: DeliveryMethod, message: Message, recipients: List[str]
    ):
        delivery_method_type = delivery_method.delivery_method_type
        sender = self._senders.get(delivery_method_type)

        if not sender:
            raise ValueError(
                f"Delivery method type {delivery_method_type} is not supported."
            )

        return sender(delivery_method, message, recipients)


senders = SenderProvider()
senders.register_sender(DeliveryMethodTypes.AWS_SES, AwsSesSender)
senders.register_sender(DeliveryMethodTypes.AWS_SNS, AwsSnsSender)
senders.register_sender(DeliveryMethodTypes.SMTP, SmtpSender)
