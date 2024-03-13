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
            # split the events list into chunks of 10 (as this is maximum number of events to put)
            def chunks(lst, n):
                """Yield successive n-sized chunks from lst."""
                for i in range(0, len(lst), n):
                    yield lst[i:i + n]
            
            # Split the events into chunks of 10
            for chunk in chunks(events, 10):
                self._events_client.put_events(Entries=chunk)
        except ClientError as e:
            raise EventsManagerClientException(
                f"Error during putting events to AWS EventBridge: {str(e)}."
            )