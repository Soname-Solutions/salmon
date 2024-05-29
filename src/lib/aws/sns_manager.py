import boto3
import json


class SNSTopicPublisherException(Exception):
    """Exception raised for errors encountered while publishing message to the SNS topic."""

    pass


class SnsTopicPublisher:
    """
    This class provides an interface to publish messages to a specified Amazon SNS topic.
    It uses the AWS SDK for Python (Boto3) to interact with the
    SNS service.

    Attributes:
        topic_arn (str): The arn of the SNS topic.
        sns_client: The Boto3 SNS client. If not provided,
            a new client instance is created.

    Methods:
        publish_message(message): Publishes a message to the SNS topic.
    """

    def __init__(self, topic_arn: str, sns_client=None):
        """
        Initializes a new SnsTopicPublisher instance.

        Args:
            topic_arn (str): The arn of the SNS topic.
            sns_client: The Boto3 SNS client. If not provided,
                a new client instance is created.
        """
        self.topic_arn = topic_arn
        self.sns_client = boto3.client("sns") if sns_client is None else sns_client

    def publish_message(self, message: dict, subject: str = None):
        """
        Publishes a message to the SNS topic.

        Args:
            message: A message dictionary array to be sent to the SNS topic.

        Returns:
            The responses from the SNS publish API calls.

        """
        try:
            formatted_message = json.dumps(message, indent=4)

            if subject:
                self.sns_client.publish(
                    TopicArn=self.topic_arn,
                    Message=formatted_message,
                    Subject=subject
                )
            else:
                self.sns_client.publish(
                    TopicArn=self.topic_arn,
                    Message=formatted_message,
                )
        except Exception as e:
            error_message = f"Error publishing messages to {self.topic_arn}: {e}"
            raise SNSTopicPublisherException(error_message)
