import boto3
import botocore
from email.message import Message as BaseEmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, TYPE_CHECKING

from .base import Sender
from ..exceptions import AwsSesSenderException, AwsSesUserNotVerifiedException, AwsSesNoRelevantRecipientsException

if TYPE_CHECKING:
    from ..messages import Message, File


class AwsSesSender(Sender):
    """Class to send a message by AWS SES."""

    def __init__(self, message: Message, sender: str, recipients: List[str]) -> None:
        """Initiate class AwsSesSender.

        Args:
            message (Message): Message to send
            sender (str): Email from
            recipients (List[str]): Emails to
        """
        super().__init__(message)
        self._ses_client = boto3.client('ses')
        self._sender = sender
        self._recipients = recipients
        self.verified_recipients = []


    @property
    def verified_recipients(self) -> List[str]:
        return self._verified_recipients


    @verified_recipients.setter
    def verified_recipients(self, recepients: List[str]) -> None:
        self._verified_recipients = recepients


    def _get_identities(self, next_token: str=None) -> List[str]:
        kwargs = {"IdentityType": "EmailAddress", "MaxItems": 1000}

        if next_token is not None:
            kwargs.update({"NextToken": next_token})

        response = self._ses_client.list_identities(**kwargs)

        identities = response['Identities']
        next_token = response.get('NextToken')

        if next_token is None:
            return identities
        else:
            return (identities + self._get_identities(next_token))


    def _get_verification_status(self, identity: str):
        return self._ses_client.get_identity_verification_attributes(
            Identities=[identity]
        )['VerificationAttributes'][identity]['VerificationStatus']


    def get_verified_emails(self):
        return [identity for identity in self._get_identities()
                if self._get_verification_status(identity) == "Success"]

    
    def set_verified_recepients(self, verified_emails: List[str]) -> None:
        self.verified_recipients = [recipient for recipient in self._recipients
                                    if recipient in verified_emails]

    def _get_message(self) -> BaseEmailMessage:
        """Get message to send."""
        charset = "utf-8"

        message = MIMEMultipart('mixed')
        message_body = MIMEMultipart('alternative')

        message['Subject'] = self._message.header
        message['From'] = self._sender
        message['To'] = ",".join(self.verified_recipients)

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
    

    def pre_process(self) -> None:
        verified_emails = self.get_verified_emails()
        self.set_verified_recepients(verified_emails)

        skipped_recepients = [recipient for recipient in self._recipients if recipient not in verified_emails]
        
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
            self._ses_client.send_raw_email(
                RawMessage={'Data': self._get_message().as_string()}
                )
        except botocore.exceptions.ClientError as ex:
            raise AwsSesSenderException(f"Error during sending message to {self.verified_recipients} "
                                        f'by {self.__class__.__name__}: {str(ex)}.') from ex
        

def create_aws_ses_sender(message: Message, ses_sender: str, recipients: List[str], **_ignored):
    """Create an AwsSesSender instance."""
    return AwsSesSender(message, ses_sender, recipients)
