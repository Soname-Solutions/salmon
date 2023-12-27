import boto3


class CloudWatchEventsPublisherException(Exception):
    """Exception raised for errors encountered while publishing message to the CloudWatch stream."""

    pass


class CloudWatchEventsPublisher:
    """
    This class provides an interface to publish messages to a specified Amazon CloudWatch stream.
    It uses the AWS SDK for Python (Boto3) to interact with the
    CloudWatch service.

    Attributes:
        log_group_name (str): The name of the CloudWatch group.
        log_stream_name (str): The name of the CloudWatch stream.
        cloudwatch_client: The Boto3 CloudWatch client. If not provided,
            a new client instance is created.

    Methods:
        put_event(time, event): Publishes a message to the CloudWatch stream.
    """

    def __init__(
        self, log_group_name: str, log_stream_name: str, cloudwatch_client=None
    ):
        """
        Initializes a new CloudWatchEventsPublisher instance.

        Args:
            log_group_name (str): The name of the CloudWatch group.
            log_stream_name (str): The name of the CloudWatch stream.
            cloudwatch_client: The Boto3 CloudWatch client. If not provided,
                a new client instance is created.
        """
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name
        self.cloudwatch_client = (
            boto3.client("logs") if cloudwatch_client is None else cloudwatch_client
        )

    def put_event(self, time: int, event: str):
        """
        Publishes a message to the CloudWatch stream.

        Args:
            time: Event time in epoch milliseconds.
            event: An event string to be sent to the CloudWatch stream.

        Returns:
            The response from the CloudWatch put_log_events API calls.

        """
        try:
            return self.cloudwatch_client.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=[{"timestamp": time, "message": event}],
            )
        except Exception as e:
            error_message = f"Error publishing events to {self.log_group_name} : {self.log_stream_name}: {e}"
            raise CloudWatchEventsPublisherException(error_message)
