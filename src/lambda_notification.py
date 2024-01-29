from lib.aws.sns_manager import SnsTopicPublisher
from lib.notification_service.formatter_provider import formatters
from lib.notification_service.sender_provider import senders
from lib.notification_service.messages import Message
from lib.aws.secret_manager import SecretManager

import logging
import json
import boto3
import os


logger = logging.getLogger()
logger.setLevel(logging.INFO)
sns_client = boto3.client("sns")


def _get_formatted_message(message_body: list, delivery_method: str) -> str:
    formatted_message_objects = []
    formatter = formatters.get(delivery_method)

    for message_object in message_body:
        try:
            object_type = [key for key in message_object.keys() if key != "style"][0]
        except IndexError:
            raise KeyError(f"Message object type {object_type} is not set.")

        content = message_object.get(object_type)
        style = message_object.get("style")

        formatted_object = formatter.format(object_type, content=content, style=style)

        if formatted_object is not None:
            formatted_message_objects.append(formatted_object)

    formatted_message_body = "".join(formatted_message_objects)
    formatted_message = formatter.get_complete_html(formatted_message_body)

    return formatted_message


def lambda_handler(event, context):
    """
    Lambda function to process event data, and send the message via the delivery method.

    Args:
        event (object): Event data containing details about the AWS resource state change.
        context: (object): AWS Lambda context (not utilized in this function).
    """
    logging.info(f"Event: {event}")

    sns_publisher = SnsTopicPublisher(
        os.environ["INTERNAL_ERROR_TOPIC_ARN"], sns_client
    )

    try:
        event_record = event.get("Records")[0]
        notification_message = json.loads(event_record.get("body"))
        delivery_options_info = notification_message.get("delivery_options")
        message_info = notification_message.get("message")

        delivery_method = delivery_options_info.get("delivery_method")

        if delivery_method is None:
            raise KeyError("Delivery method is not set.")

        message_subject = message_info.get("message_subject")
        message_body = message_info.get("message_body")

        if message_subject is None:
            raise KeyError("Message subject is not set.")

        if message_body is None:
            raise KeyError("Message body is not set.")

        delivery_method_type = delivery_method.get("delivery_method_type")
        formatted_message = _get_formatted_message(message_body, delivery_method_type)

        message = Message(formatted_message, message_subject)

        secret_client = SecretManager()
        smtp_secret_name = delivery_options_info.get("smtp_secret_name")
        smtp_secret = secret_client.get_secret(smtp_secret_name)

        sender = senders.get(
            delivery_method=delivery_method_type,
            message=message,
            ses_sender=delivery_method.get("sender_email"),
            recipients=delivery_options_info.get("recipients"),
            smtp_sender=smtp_secret["SMTP_SENDER"],
            smtp_server=smtp_secret["SMTP_SERVER"],
            smtp_port=smtp_secret["SMTP_PORT"],
            smtp_login=smtp_secret["SMTP_LOGIN"],
            smtp_password=smtp_secret["SMTP_PASSWORD"],
        )

        sender.pre_process()

        sender.send()

    except Exception as e:
        logger.error(f"Error while processing an event: {e}")
        event["errorMessage"] = str(e)
        event["errorType"] = e.__class__.__name__
        sns_publisher.publish_message(event)

    return {"event": event}
