import pytest

from lib.notification_service.formatter import HtmlFormatter
from lib.settings.settings_classes import DeliveryMethod

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

DELIVERY_METHOD_CSS_CLASSES = DeliveryMethod(
    name="ses", delivery_method_type="AWS_SES"
)  # Assuming by default "use_inline_css_styles"=True

######################################################################################


def test_get_formatted_message_html_valid():
    formatter = HtmlFormatter(DELIVERY_METHOD_CSS_CLASSES)
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

    formatter = HtmlFormatter(DELIVERY_METHOD_CSS_CLASSES)
    with pytest.raises(KeyError):
        formatted_message = formatter.get_formatted_message(message_body)


@pytest.mark.parametrize(
    "css_class_name, css_definition, delivery_method, expected_tag",
    [
        # should convert into 'div style=...'
        (
            "test_class",
            {"color": "red"},
            DeliveryMethod(
                name="test_method",
                delivery_method_type="AWS_SES",
                use_inline_css_styles=True,
            ),
            'style="color: red"',
        ),
        # should render into 'div class=...'
        (
            "test_class",
            {"color": "red"},
            DeliveryMethod(
                name="test_method",
                delivery_method_type="AWS_SES",
                use_inline_css_styles=False,
            ),
            'class="test_class"',
        ),
        # testing default (should be False)
        # so should render into 'div class=...'
        (
            "test_class",
            {"color": "red"},
            DeliveryMethod(name="test_method", delivery_method_type="AWS_SES"),
            'class="test_class"',
        ),
    ],
)
def test_use_inline_css_styles(
    css_class_name, css_definition, delivery_method, expected_tag
):
    message_body = [{"text": "Something bad has happened", "style": css_class_name}]

    formatter = HtmlFormatter(delivery_method)
    formatter._css_style_dict[f".{css_class_name}"] = css_definition

    formatted_message = formatter.get_formatted_message(message_body)

    soup = BeautifulSoup(formatted_message, "html.parser")
    div = soup.find_all("div")

    assert len(div) == 1, "There should be exactly one <div> element"
    div_content: str = str(div[0])

    assert (
        expected_tag in div_content
    ), f"<div> should contain {expected_tag} (returned content = {div_content})"
