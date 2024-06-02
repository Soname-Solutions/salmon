import pytest

from lib.notification_service.formatter import HtmlFormatter

from bs4 import BeautifulSoup

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

def test_get_formatted_message_html_valid():
    formatter = HtmlFormatter()   
    formatted_message = formatter.get_formatted_message(TEST_MESSAGE_BODY)

    soup = BeautifulSoup(formatted_message, "html.parser")
    assert soup.find() is not None, "The output should be valid HTML"
    assert soup.find("table") is not None, "The output should contain an HTML table"
    assert "AWS Account" in formatted_message, "The output should contain 'AWS Account'"
    assert (
        "1234567890" in formatted_message
    ), "The output should contain the account number '1234567890'"


def test_get_formatted_message_missing_key_raises_key_error():
    message_body = [
        {"style": "header_777"}
    ]  # Missing required key, thus should raise KeyError

    formatter = HtmlFormatter()   
    with pytest.raises(KeyError):
        formatted_message = formatter.get_formatted_message(message_body)

