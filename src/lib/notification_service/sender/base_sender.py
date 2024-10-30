from abc import ABC, abstractmethod
from ..messages import Message
from typing import List
from lib.settings.settings_classes import DeliveryMethod


class BaseSender(ABC):
    def __init__(
        self, delivery_method: DeliveryMethod, message: Message, recipients: List[str]
    ) -> None:
        """Ititiate base sender class.

        Args
            delivery_method (dict): Delivery method information
            message (Message): Message to send.
            recipients (List[str]): List of recipient emails
        """
        self._delivery_method = delivery_method
        self._message = message
        self._recipients = recipients

    def pre_process(self) -> None:
        """Do preparations before sending a message."""
        pass

    @abstractmethod
    def send(self) -> None:
        """Send the message."""
        pass
