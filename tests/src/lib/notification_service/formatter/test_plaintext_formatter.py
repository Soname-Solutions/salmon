import pytest

from lib.notification_service.formatter import PlainTextFormatter

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

######################################################################################

def test_get_formatted_message_valid():
    formatter = PlainTextFormatter()   
    formatted_message = formatter.get_formatted_message(TEST_MESSAGE_BODY)

    assert "Something bad has happened"  in formatted_message
    assert "1234567890"  in formatted_message



def test_get_formatted_message_missing_key_raises_key_error():
    message_body = [
        {"style": "header_777"}
    ]  # Missing required key, thus should raise KeyError

    formatter = PlainTextFormatter()   
    with pytest.raises(KeyError):
        formatted_message = formatter.get_formatted_message(message_body)

