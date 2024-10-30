from typing import List

from .base_sender import BaseSender
from ..messages import Message, File
from lib.aws.sns_manager import SnsTopicPublisher, SNSTopicPublisherException
from lib.settings.settings_classes import DeliveryMethod


class AwsSnsSenderException(Exception):
    """Exception raised for errors encountered while sending message to SNS topic."""

    pass


class AwsSnsSender(BaseSender):
    """Class to send a message by AWS SES."""

    def __init__(
        self, delivery_method: DeliveryMethod, message: Message, recipients: List[str]
    ) -> None:
        """Initiate class AwsSnsSender.

        Args:
            delivery_method (DeliveryMethod): Delivery method information
            message (Message): Message to send
            recipients (List[str]): List of SNS topic Arns to publish to
        """
        super().__init__(delivery_method, message, recipients)

    def send(self) -> None:
        try:
            for topic_arn in self._recipients:
                sns_publisher = SnsTopicPublisher(topic_arn=topic_arn)
                sns_publisher.publish_message(
                    message=self._message.body, subject=self._message.subject
                )
        except Exception as ex:
            raise AwsSnsSenderException(
                f"Error while sending a message to {self._recipients} "
                f"by {self.__class__.__name__}: {str(ex)}."
            ) from ex
