import pytest

from lib.notification_service.formatter import PlainTextFormatter
from lib.settings.settings_classes import DeliveryMethod

TEST_MESSAGE_BODY = [
    {"text": "Something bad has happened", "style": "header_777"},
    {
        "table": {
            "rows": [
                {"values": ["AWS Account", "1234567890"]},
                {"values": ["AWS Region", "eu-central-1"]},
            ]
        }
    },
]

DELIVERY_METHOD_DEFAULT = DeliveryMethod(name="sns", delivery_method_type="AWS_SNS")

######################################################################################


def test_get_formatted_message_valid():
    formatter = PlainTextFormatter(DELIVERY_METHOD_DEFAULT)
    formatted_message = formatter.get_formatted_message(TEST_MESSAGE_BODY)

    assert "Something bad has happened" in formatted_message
    assert "1234567890" in formatted_message


def test_get_formatted_message_missing_key_raises_key_error():
    message_body = [
        {"style": "header_777"}
    ]  # Missing required key, thus should raise KeyError

    formatter = PlainTextFormatter(DELIVERY_METHOD_DEFAULT)
    with pytest.raises(KeyError):
        formatted_message = formatter.get_formatted_message(message_body)


# actually it's a test covering BaseFormatter functionality
def test_exception_unknown_element():
    # Adding not recognized "weird_element"
    element_name = "weird_element"
    message_body = [{element_name: "some stuff", "style": "none"}]

    formatter = PlainTextFormatter(DELIVERY_METHOD_DEFAULT)
    with pytest.raises(
        ValueError, match=f"Message object type {element_name} is not supported"
    ):
        formatted_message = formatter.get_formatted_message(message_body)
