from email.message import Message as BaseEmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL, SMTPResponseException
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
        self._sender_email = self._delivery_method.get("sender_email")
        self._use_ssl = self._delivery_method.get("use_ssl", True)
        self._timeout = self._delivery_method.get("timeout", 10.0)

    def _get_message(self) -> BaseEmailMessage:
        """Get message to send."""
        charset = "utf-8"

        message = MIMEMultipart("mixed")
        message_body = MIMEMultipart("alternative")

        message["Subject"] = self._message.subject
        message["From"] = self._sender_email
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
    def _get_smtp_credential_property(smtp_secret, property_name):
        smtp_property = smtp_secret.get(property_name)
        if smtp_property is None:
            raise KeyError(
                f"SMTP property {property_name} is not defined in the secret."
            )
        return smtp_property

    @staticmethod
    def _get_file_mime_object(file: File) -> MIMEBase:
        """Get MIME-object of a file to attach."""
        mime_type, mime_subtype = file.mime_type.split("/")[:2]
        mime_object = MIMEBase(mime_type, mime_subtype)
        mime_object.set_payload(file.content)
        mime_object.add_header("Content-Disposition", "attachment", filename=file.name)
        return mime_object

    def _send_via_ssl(
        self,
        smtp_server: str,
        port: int,
        login: str,
        password: str,
        context: ssl.SSLContext,
    ) -> None:
        """Send email via SMTP SSL."""
        with SMTP_SSL(
            host=smtp_server, port=port, timeout=self._timeout, context=context
        ) as server:
            server.login(user=login, password=password)
            server.sendmail(
                from_addr=self._sender_email,
                to_addrs=self._recipients,
                msg=self._get_message().as_string(),
            )

    def _send_via_starttls(
        self,
        smtp_server: str,
        port: int,
        login: str,
        password: str,
        context: ssl.SSLContext,
    ) -> None:
        """Send email via SMTP STARTTLS."""
        with SMTP(host=smtp_server, port=port, timeout=self._timeout) as server:
            server.starttls(context=context)
            server.login(user=login, password=password)
            server.sendmail(
                from_addr=self._sender_email,
                to_addrs=self._recipients,
                msg=self._get_message().as_string(),
            )

    def send(self) -> None:
        """Send a message via SMTP."""
        context = ssl.create_default_context()
        smtp_secret_name = self._delivery_method.get("credentials_secret_name")

        if smtp_secret_name is None:
            raise KeyError("Credentials Secret Name is not set.")

        smtp_secret = self._secret_client.get_secret(secret_name=smtp_secret_name)
        smtp_server = self._get_smtp_credential_property(smtp_secret, "SMTP_SERVER")
        port = int(self._get_smtp_credential_property(smtp_secret, "SMTP_PORT"))
        login = self._get_smtp_credential_property(smtp_secret, "SMTP_LOGIN")
        password = self._get_smtp_credential_property(smtp_secret, "SMTP_PASSWORD")

        try:
            if self._use_ssl and port != 25:
                self._send_via_ssl(smtp_server, port, login, password, context)
            else:
                self._send_via_starttls(smtp_server, port, login, password, context)
        except SMTPResponseException as ex:
            raise SmtpSenderException(
                f"Error during sending message to {self._recipients} "
                f"by {self.__class__.__name__}: {str(ex)}."
            ) from ex
