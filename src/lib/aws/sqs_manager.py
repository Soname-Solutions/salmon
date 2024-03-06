import boto3
import json


class SQSQueueSenderException(Exception):
    """Exception raised for errors encountered while sending message to the SQS queue."""

    pass


class SQSQueueSender:
    """
    This class provides an interface to send messages to a specified Amazon SQS queue.
    It uses the AWS SDK for Python (Boto3) to interact with the
    SQS service.

    Attributes:
        queue_url (str): The url of the SQS queue.
        message_group_id (str): The tag that specifies that a message belongs to
            a specific message group. The max length is 128 characters.
        sqs_client: The Boto3 SQS client. If not provided,
            a new client instance is created.

    Methods:
        send_message(message): Sends a message to the SQS queue.
    """

    def __init__(self, queue_url: str, message_group_id: str, sqs_client=None):
        """
        Initializes a new SQSQueueSender instance.

        Args:
            queue_url (str): The url of the SQS queue.
            message_group_id (str): The tag that specifies that a message belongs to
                a specific message group. The max length is 128 characters.
            sqs_client: The Boto3 SQS client. If not provided,
                a new client instance is created.
        """
        self.queue_url = queue_url
        self.message_group_id = message_group_id[:128]
        self.sqs_client = boto3.client("sqs") if sqs_client is None else sqs_client

    def send_messages(self, messages: list[dict]):
        """
        Sends messages to the SQS queue.

        Args:
            message: A message dictionary array to be sent to the SQS queue.

        Returns:
            The responses from the SQS send_message API calls.

        """
        results = []
        for message in messages:
            try:
                result = self.sqs_client.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(message, indent=4),
                    MessageGroupId=self.message_group_id,
                )
                results.append(result)
            except Exception as e:
                error_message = f"Error sending messages to {self.queue_url}: {e}"
                raise SQSQueueSenderException(error_message)

        return results
