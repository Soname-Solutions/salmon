import requests
import json

from typing import List

from .sender import Sender
from ..messages import Message, File


class SlackSenderException(Exception):
    """Exception raised for errors encountered while sending message to Slack channel."""

    pass


class SlackSender(Sender):
    """Class to send a message by AWS SES."""

    def __init__(
        self, delivery_method: dict, message: Message, recipients: List[str]
    ) -> None:
        """Initiate class SlackSender.

        Args:
            delivery_method (dict): Delivery method information
            message (Message): Message to send
            recipients (List[str]): List of SNS topic Arns to publish to
        """
        super().__init__(delivery_method, message, recipients)

    def send(self) -> None:
        try:
            for webhook_url in self._recipients:
                slack_data = {
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": self._message.subject},
                        },
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": json.dumps(
                                    self._message.body, indent=4, default=str
                                ),
                            },
                        },
                    ]
                }

                # Send the message to Slack
                response = requests.post(
                    webhook_url,
                    data=json.dumps(slack_data),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code != 200:
                    raise ValueError(
                        f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}"
                    )

        except Exception as ex:
            raise SlackSenderException(
                f"Error while sending a message to {self._recipients} "
                f"by {self.__class__.__name__}: {str(ex)}."
            ) from ex
