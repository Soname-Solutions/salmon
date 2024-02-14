from email.message import Message as BaseEmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPResponseException
import json
import ssl

from typing import List
from .sender import Sender
from ..exceptions import SmtpSenderException
from ..messages.message import Message, File
from ...aws.secret_manager import SecretManager


class SmtpSender(Sender):
    def __init__(
        self,
        delivery_method: dict,
        message: Message,
        recipients: List[str],
    ) -> None:
        """Initiate class EmailSender."""
        super().__init__(delivery_method, message, recipients)
        self._secret_client = SecretManager()

    def _get_message(self) -> BaseEmailMessage:
        """Get message to send."""
        charset = "utf-8"

        message = MIMEMultipart("mixed")
        message_body = MIMEMultipart("alternative")

        message["Subject"] = self._message.header
        message["From"] = self._delivery_method.get("sender_email")
        message["To"] = ",".join(self._recipients)

        # Encode the text and HTML content and set the character encoding. This step is
        # necessary if you're sending a message with characters outside the ASCII range.
        # textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
        html_body = MIMEText(self._message.body.encode(charset), "html", charset)

        message_body.attach(html_body)
        message.attach(message_body)

        if self._message.file is not None:
            message.attach(self._get_file_mime_object(self._message.file))

        return message

    @staticmethod
    def _get_file_mime_object(file: File) -> MIMEBase:
        """Get MIME-object of a file to attach."""
        mime_type, mime_subtype = file.mime_type.split("/")[:2]
        mime_object = MIMEBase(mime_type, mime_subtype)
        mime_object.set_payload(file.content)
        mime_object.add_header("Content-Disposition", "attachment", filename=file.name)
        return mime_object

    def send(self) -> None:
        """Send a message via SMTP."""
        context = ssl.create_default_context()
        smtp_secret_name = self._delivery_method.get("credentials_secret_name")

        if smtp_secret_name is None:
            raise KeyError("Credentials Secret Name is not set.")

        smtp_secret = json.loads(self._secret_client.get_secret(smtp_secret_name))
        smtp_server = smtp_secret["SMTP_SERVER"]
        port = smtp_secret["SMTP_PORT"]
        login = smtp_secret["SMTP_LOGIN"]
        password = smtp_secret["SMTP_PASSWORD"]

        with SMTP_SSL(smtp_server, port, context=context) as server:
            try:
                server.login(login, password)
                server.sendmail(
                    self._delivery_method.get("sender_email"),
                    self._recipients,
                    self._get_message().as_string(),
                )
            except SMTPResponseException as ex:
                raise SmtpSenderException(
                    f"Error during sending message to {self._recipients} "
                    f"by {self.__class__.__name__}: {str(ex)}."
                ) from ex


def create_smtp_sender(
    delivery_method: dict,
    message: Message,
    recipients: List[str],
):
    """Create an SmtpSender instance."""
    return SmtpSender(
        delivery_method,
        message,
        recipients,
    )
