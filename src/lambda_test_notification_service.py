from lib.notification_service.formatter_provider import formatters
from lib.notification_service.sender_provider import senders
from lib.notification_service.messages import Message


# todo: the config will be read from settings config
sender_config = {
    "smtp_sender": "my_email@soname.de",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "smtp_login": "my_email@soname.de",
    "smtp_password": "my_pass",
}


def _get_formatted_message_body(message_body: list, delivery_method: str) -> str:
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

    return "".join(formatted_message_objects)


def lambda_handler(event, context):
    """
    Lambda function to process event data, and send the message via the delivery method.

    Args:
        event (object): Event data containing details about the AWS resource state change.
        context: (object): AWS Lambda context (not utilized in this function).
    """
    delivery_options_info = event.get("delivery_options")
    message_info = event.get("message")

    delivery_method = delivery_options_info.get("delivery_method")

    if delivery_method is None:
        raise KeyError("Delivery method is not set.")

    message_subject = message_info.get("message_subject")
    message_body = message_info.get("message_body")

    if message_subject is None:
        raise KeyError("Message subject is not set.")

    if message_body is None:
        raise KeyError("Message body is not set.")

    formatted_message_body = _get_formatted_message_body(message_body, delivery_method)

    message = Message(formatted_message_body, message_subject)

    sender = senders.get(
        delivery_method,
        message=message,
        ses_sender=delivery_options_info.get("sender_email"),
        recipients=delivery_options_info.get("recipients"),
        **sender_config,
    )

    try:
        sender.pre_process()
    except Exception as ex:
        print(ex)

    sender.send()


if __name__ == "__main__":
    test_event = {
        "delivery_options": {
            "sender_email": "salmon-no-reply@soname.de",
            "recipients": ["vasya_pupking@soname.cn"],
            "delivery_method": "AWS_SES",
        },
        "message": {
            "message_subject": "Super important Alert",
            "message_body": [
                {"text": "Daily monitoring report", "style": "header_777"},
                {
                    "table": {
                        "caption": "My Lovely Table",
                        "header": {
                            "values": ["colname1", "colname2", "colname3"],
                            "style": "error",
                        },
                        "rows": [
                            {
                                "values": ["colname1", "colname2", "colname3"],
                                "style": "error",
                            },
                            {
                                "values": ["colname1", "colname2", "colname3"],
                                "style": "error",
                            },
                        ],
                    }
                },
                {"text": "Daily monitoring report", "style": "header_1"},
                {
                    "table": {
                        "caption": "My Lovely Table",
                        "header": {
                            "values": ["colname1", "colname2", "colname3"],
                            "style": "error",
                        },
                        "rows": [
                            {
                                "values": ["colname1", "colname2", "colname3"],
                                "style": "error",
                            }
                        ],
                    }
                },
            ],
        },
    }
    context = ""

    lambda_handler(test_event, context)
