import json

from constants import NotificationServiceConfig

from notification_service.sender_provider import senders
from notification_service.messages import Message

# todo: the config will be read from settings config
sender_config = {
    "ses_sender": NotificationServiceConfig.SES_SENDER,
    "smtp_sender": NotificationServiceConfig.SMTP_SENDER,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "smtp_login": NotificationServiceConfig.SMTP_SENDER,
    "smtp_password": "",
}

# todo: recipients should be got from settings
recipients = [
    "my_email@soname.de"
    # , "vasilii_pupkin@salmon.com"
]


def lambda_handler(event, context):
    """
    Lambda function to process event data, and send the message via the delivery method.

    Args:
        event (object): Event data containing details about the AWS resource state change.
        context: (object): AWS Lambda context (not utilized in this function).
    """
    delivery_info = json.loads(event)
    delivery_method = delivery_info.get("delivery_method")

    if delivery_method is None:
        raise KeyError("Delivery method is not set.")

    message = Message(
        delivery_info.get("message"), NotificationServiceConfig.ALERT_HEADER
    )
    sender = senders.get(
        delivery_method, message=message, recipients=recipients, **sender_config
    )

    try:
        sender.pre_process()
    except Exception as ex:
        print(ex)

    sender.send()


if __name__ == "__main__":
    test_event = """
        {
            "delivery_method": "AWS_SES",
            "message": "<html><head><style>table, th, td { border: 1px solid black; margin: 2px; }</style></head><body><h1>Hi</h1><table><tr><td>Glue Job 1 failed!</td></tr></table></body></html>"
        }
        """
    context = ""

    lambda_handler(test_event, context)
