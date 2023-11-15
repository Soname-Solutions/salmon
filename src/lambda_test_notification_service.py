import os
import json

from constants import NotificationServiceConfig

from notification_service.sender import AwsSesSender, Message


SUPPORTED_DELIVERY_METHODS = frozenset(["AWS_SES", "SMTP"])


def lambda_handler(event, context):
    delivery_info = json.loads(event)
    delivery_method = delivery_info.get("delivery_method")
    message = Message(delivery_info.get("message_body"), delivery_info.get("message_header"))
    recipients = delivery_info.get("recipients")

    if delivery_method is None:
        raise KeyError("Delivery method is not set.")
    
    if delivery_method == "AWS_SES":
        sender = AwsSesSender(message, sender=NotificationServiceConfig.SES_SENDER, recipients=recipients)

        verified_emails = sender.get_verified_emails()
        sender.set_verified_recepients(verified_emails)

        for recipient in recipients:
            if recipient not in verified_emails:
                print(f"Skipping notification for {recipient} - email address is not verified in SES")

        recipients = sender.verified_recipients
    elif delivery_method == "SMTP":
        pass
    elif delivery_method not in SUPPORTED_DELIVERY_METHODS:
        raise ValueError(f"Delivery method {delivery_method} is not supported.)")
    
    if recipients:
        print(f"Sending notification to recipients = {recipients}")
        sender.send()
    else:
        print("Skipping notification as there are no relevant subscribers")


if __name__ == "__main__":
    test_event = """
        {
            "recipients": ["natallia.alkhimovich@soname.de", "vasilii_pupkin@salmon.com"],
            "delivery_method": "AWS_SES",
            "message_header": "SDM [DEV] SAP Lean Glue Failure",
            "message_body": "<html><head><style>table, th, td { border: 1px solid black; margin: 2px; }</style></head><body><h1>Hi</h1><table><tr><td>Glue Job 1 failed!</td></tr></table></body></html>"
        }
        """
    context = ""

    lambda_handler(test_event, context)
