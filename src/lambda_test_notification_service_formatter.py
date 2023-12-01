from lib.notification_service.formatter_provider import formatters


def lambda_handler(event, context):
    delivery_options_info = event.get("delivery_options")
    message_info = event.get("message")

    delivery_method = delivery_options_info.get("delivery_method")

    if delivery_method is None:
        raise KeyError("Delivery method is not set.")

    message_subject = message_info.get("message_subject")
    message_body = message_info.get("message_body", [])
    formatter = formatters.get(delivery_method)

    formatted_message = []

    for message_object in message_body:
        try:
            object_type = [key for key in message_object.keys() if key != "style"][0]
        except IndexError:
            raise KeyError(f"Message object type {object_type} is not set.")

        content = message_object.get(object_type)
        style = message_object.get("style")

        formatted_object = formatter.format(object_type, content=content, style=style)

        if formatted_object is not None:
            formatted_message.append(formatted_object)

    print(formatted_message)


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
