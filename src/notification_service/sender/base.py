from abc import ABC, abstractmethod
from .message import Message


class Sender(ABC):

    def __init__(self, message: Message) -> None:
        """Ititiate base sender class.

        Args
            message (Message): Message to send.
        """
        self._message = message

    @abstractmethod
    def send(self) -> None:
        """Send the message."""
        pass
