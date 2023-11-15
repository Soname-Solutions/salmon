from typing import List

from .message import Message
from .base import Sender


class SmtpSender(Sender):

    def __init__(self, message: Message, email_from: str, email_to: List[str],
                 server: str, port: int, login: str, password: str) -> None:
        """Initiate class EmailSender."""
        super().__init__(message)
        self._email_from = email_from
        self._email_to = email_to
        self._server = server
        self._port = port
        self._login = login
        self._password = password

    def send(self) -> None:
        pass
