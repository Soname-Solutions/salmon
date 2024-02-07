import boto3
from botocore.exceptions import ClientError

class EventsManagerClientException(Exception):
    """Error while retrieving a secret from AWS EventBridge."""

    pass


class EventsManager:
    """Manages interactions with AWS EventBridge."""

    def __init__(self, events_client=None) -> None:
        """Initiate class EventsManager.

        Args:
            events_client: Boto3 SES client for AWS interactions.
        """
        self._events_client = (
            boto3.client(service_name="events")
            if events_client is None
            else events_client
        )

    def put_events(self, events: []):
        """Sends events to event bus
        Args:
            events (list): List of events to be sent to event bus.
            (in each events field EventBusName defines the target eventbus)
        """
        try:
            self._events_client.put_events(Entries=events)
        except ClientError as e:
            raise EventsManagerClientException(
                f"Error during putting events to AWS EventBridge: {str(e)}."
            )