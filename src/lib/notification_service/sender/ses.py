from email.message import Message as BaseEmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from .sender import Sender
from ..exceptions import (
    AwsSesSenderException,
    AwsSesUserNotVerifiedException,
    AwsSesNoRelevantRecipientsException,
)
from ..messages import Message, File
from ...aws import AwsSesManager, AwsSesRawEmailSenderException


class AwsSesSender(Sender):
    """Class to send a message by AWS SES."""

    def __init__(
        self, delivery_method: dict, message: Message, recipients: List[str]
    ) -> None:
        """Initiate class AwsSesSender.

        Args:
            delivery_method (dict): Delivery method information
            message (Message): Message to send
            sender_email (str): Email from
            recipients (List[str]): Emails to
        """
        super().__init__(delivery_method, message, recipients)
        self._ses_manager = AwsSesManager()
        self.verified_recipients = []

    @property
    def verified_recipients(self) -> List[str]:
        """Verified by AWS SES recipiens."""
        return self._verified_recipients

    @verified_recipients.setter
    def verified_recipients(self, recepients: List[str]) -> None:
        """Verified by AWS SES recipiens."""
        self._verified_recipients = recepients

    def _get_message(self) -> BaseEmailMessage:
        """Get message to send."""
        charset = "utf-8"

        message = MIMEMultipart("mixed")
        message_body = MIMEMultipart("alternative")

        message["Subject"] = self._message.subject
        message["From"] = self._delivery_method.get("sender_email")
        message["To"] = ",".join(self.verified_recipients)

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

    def pre_process(self) -> None:
        """Set verified recepients before sending a message."""
        verified_identities = self._ses_manager.get_verified_identities()
        self.verified_recipients = [
            recipient
            for recipient in self._recipients
            if recipient in verified_identities
        ]

        skipped_recepients = [
            recipient
            for recipient in self._recipients
            if recipient not in verified_identities
        ]

        if skipped_recepients:
            raise AwsSesUserNotVerifiedException(
                f"Email addresses {', '.join(skipped_recepients)} are not verified in SES."
            )

    def send(self) -> None:
        """Send a message via AWS SES."""
        if not self.verified_recipients:
            raise AwsSesNoRelevantRecipientsException(
                "Skipping sending message due to no relevant recepients."
            )

        try:
            self._ses_manager.send_raw_email(self._get_message().as_string())
        except AwsSesRawEmailSenderException as ex:
            raise AwsSesSenderException(
                f"Error during sending message to {self.verified_recipients} "
                f"by {self.__class__.__name__}: {str(ex)}."
            ) from ex
