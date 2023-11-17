from email.message import Message as BaseEmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPResponseException
import ssl

from typing import List
from .base import Sender
from ..exceptions import SmtpSenderException
from ..messages.message import Message, File


class SmtpSender(Sender):

    def __init__(self, message: Message, sender: str, recipients: List[str],
                 server: str, port: int, login: str, password: str) -> None:
        """Initiate class EmailSender."""
        super().__init__(message)
        self._sender = sender
        self._recipients = recipients
        self._server = server
        self._port = port
        self._login = login
        self._password = password


    def _get_message(self) -> BaseEmailMessage:
        """Get message to send."""
        charset = "utf-8"

        message = MIMEMultipart('mixed')
        message_body = MIMEMultipart('alternative')

        message['Subject'] = self._message.header
        message['From'] = self._sender
        message['To'] = ",".join(self._recipients)

        # Encode the text and HTML content and set the character encoding. This step is
        # necessary if you're sending a message with characters outside the ASCII range.
        #textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
        html_body = MIMEText(self._message.body.encode(charset), 'html', charset)

        message_body.attach(html_body)
        message.attach(message_body)

        if self._message.file is not None:
            message.attach(self._get_file_mime_object(self._message.file))

        return message
    
    
    @staticmethod
    def _get_file_mime_object(file: File) -> MIMEBase:
        """Get MIME-object of a file to attach."""
        mime_type, mime_subtype = file.mime_type.split('/')[:2]
        mime_object = MIMEBase(mime_type, mime_subtype)
        mime_object.set_payload(file.content)
        mime_object.add_header('Content-Disposition', 'attachment', filename=file.name)
        return mime_object


    def send(self) -> None:
        """Send a message via SMTP."""
        context = ssl.create_default_context()

        with SMTP_SSL(self._server, self._port, context=context) as server:
            try:
                server.login(self._login, self._password)
                server.sendmail(self._sender, self._recipients, self._get_message().as_string())
            except SMTPResponseException as ex:
                raise SmtpSenderException(f"Error during sending message to {self._recipients} "
                                          f"by {self.__class__.__name__}: {str(ex)}.") from ex


def create_smtp_sender(message: Message, smtp_sender: str, recipients: List[str], 
                       smtp_server: str, smtp_port: int, smtp_login: str, smtp_password: str, **_ignored):
    """Create an SmtpSender instance."""
    return SmtpSender(message, smtp_sender, recipients, smtp_server, smtp_port, smtp_login, smtp_password)
