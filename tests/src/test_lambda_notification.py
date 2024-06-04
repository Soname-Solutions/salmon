from lambda_notification import lambda_handler
from lib.aws.sns_manager import SnsTopicPublisher

import copy
import os
import json
import pytest
from unittest.mock import patch, Mock, MagicMock

# uncomment this to see lambda's logging output
# import logging

# logger = logging.getLogger()
# logger.setLevel(logging.INFO)
# handler = logging.StreamHandler()
# logger.addHandler(handler)

######################################################################################

TEST_EVENT_ALERT_SES = {
    "delivery_options": {
        "delivery_method": {
            "name": "primary_ses",
            "delivery_method_type": "AWS_SES",
            "sender_email": "no-reply@company.com",
        },
        "recipients": ["admin1@company.com", "admin2@company.com"],
    },
    "message": {
        "message_subject": "Account1 [dev]: FAILED - glue_jobs : sample-job",
        "message_body": [
            {"text": "Something bad has happened", "style": "header_777"},
            {
                "table": {
                    "rows": [
                        {"values": ["AWS Account", "1234567890"]},
                        {"values": ["AWS Region", "eu-central-1"]},
                    ]
                }
            },
        ],
    },
}
######################################################################################


@pytest.fixture(scope="session", autouse=True)
def os_vars_init(aws_props_init):
    # Sets up necessary lambda OS vars
    (account_id, region) = aws_props_init
    stage_name = "teststage"
    os.environ["INTERNAL_ERROR_TOPIC_ARN"] = (
        f"arn:aws:sns:{region}:{account_id}:topic-salmon-internal-error-{stage_name}"
    )


@pytest.fixture(
    scope="function"
)  # scope is function as we check exact number of sns calls for each test
def mock_sns_publisher():
    with patch.object(
        SnsTopicPublisher, "publish_message", autospec=True
    ) as mock_publish_message:
        yield mock_publish_message


@pytest.fixture(scope="function")
def mock_sender():
    with patch("lambda_notification.senders.get", autospec=True) as mock_senders_get:
        mock_sender_instance = MagicMock()
        mock_sender_instance.pre_process = MagicMock()
        mock_sender_instance.send = MagicMock()
        mock_senders_get.return_value = mock_sender_instance
        yield mock_senders_get, mock_sender_instance

######################################################################################
# Tests for lambda_handler


def test_lambda_handler_success(mock_sns_publisher, mock_sender):
    mock_senders_get, mock_sender_instance = mock_sender

    event = {"Records": [{"body": json.dumps(TEST_EVENT_ALERT_SES)}]}

    result = lambda_handler(event, None)

    # Assert that the mocked methods were called as expected
    mock_senders_get.assert_called_once()
    mock_sender_instance.pre_process.assert_called_once()
    mock_sender_instance.send.assert_called_once()
    mock_sns_publisher.assert_not_called()  # Ensures no error publishing was needed

    # Optionally, assert the return value or other side effects
    assert (
        result["event"] == event
    ), "The function should return the original event in case of success"


def missing_fields_check(last_call_args, expected_error_type, expected_error_message):
    assert (
        expected_error_type in last_call_args
    ), f"Expected error type {expected_error_type} not found in the call arguments"
    assert (
        expected_error_message in last_call_args
    ), f"Expected error message {expected_error_message} not found in the call arguments"


def test_lambda_handler_no_delivery_method(mock_sns_publisher):
    alert_data = copy.deepcopy(TEST_EVENT_ALERT_SES)
    alert_data["delivery_options"].pop("delivery_method", None)
    event = {"Records": [{"body": json.dumps(alert_data)}]}

    lambda_handler(event, {})

    mock_sns_publisher.assert_called_once()  # check if we've got internal SNS notification
    missing_fields_check(
        str(mock_sns_publisher.call_args[0][1]),
        "KeyError",
        "Delivery method is not set",
    )


def test_lambda_handler_no_delivery_method_type(mock_sns_publisher):
    alert_data = copy.deepcopy(TEST_EVENT_ALERT_SES)
    alert_data["delivery_options"]["delivery_method"].pop("delivery_method_type", None)
    event = {"Records": [{"body": json.dumps(alert_data)}]}

    lambda_handler(event, {})

    mock_sns_publisher.assert_called_once()  # check if we've got internal SNS notification
    missing_fields_check(
        str(mock_sns_publisher.call_args[0][1]),
        "KeyError",
        "Delivery method type is not set",
    )


def test_lambda_handler_no_message_subject(mock_sns_publisher):
    alert_data = copy.deepcopy(TEST_EVENT_ALERT_SES)
    alert_data["message"].pop("message_subject", None)
    event = {"Records": [{"body": json.dumps(alert_data)}]}

    lambda_handler(event, {})

    mock_sns_publisher.assert_called_once()  # check if we've got internal SNS notification
    missing_fields_check(
        str(mock_sns_publisher.call_args[0][1]),
        "KeyError",
        "Message subject is not set",
    )


def test_lambda_handler_no_message_body(mock_sns_publisher):
    alert_data = copy.deepcopy(TEST_EVENT_ALERT_SES)
    alert_data["message"].pop("message_body", None)
    event = {"Records": [{"body": json.dumps(alert_data)}]}

    lambda_handler(event, {})

    mock_sns_publisher.assert_called_once()  # check if we've got internal SNS notification
    missing_fields_check(
        str(mock_sns_publisher.call_args[0][1]), "KeyError", "Message body is not set"
    )
