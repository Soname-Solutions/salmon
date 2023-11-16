from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..messages import Message


class Sender(ABC):

    def __init__(self, message: Message) -> None:
        """Ititiate base sender class.

        Args
            message (Message): Message to send.
        """
        self._message = message

    def pre_process(self) -> None:
        pass


    @abstractmethod
    def send(self) -> None:
        """Send the message."""
        pass
