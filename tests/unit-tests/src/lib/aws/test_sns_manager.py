import pytest
from unittest.mock import MagicMock, patch
from moto import mock_aws

from lib.aws.sns_manager import SnsTopicPublisher, SNSTopicPublisherException
import os
import boto3
import json

ACCOUNT_ID = "123456789012"
REGION_NAME = "us-east-1"
TOPIC_NAME = "fake-topic"
TOPIC_ARN = f"arn:aws:sns:{REGION_NAME}:{ACCOUNT_ID}:{TOPIC_NAME}"


@pytest.fixture
def aws_sns_client():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

    with mock_aws():
        yield boto3.client("sns", region_name=REGION_NAME)


def test_json_message_no_subject():
    mock_sns_client = MagicMock()
    sns_publisher = SnsTopicPublisher(topic_arn=TOPIC_ARN, sns_client=mock_sns_client)

    message = {"key": "value"}
    expected_formatted_message = json.dumps(message, indent=4)

    sns_publisher.publish_message(message=message)

    mock_sns_client.publish.assert_called_with(
        TopicArn=TOPIC_ARN,
        Message=expected_formatted_message,
    )


def test_plaintext_message_with_subject():
    mock_sns_client = MagicMock()
    sns_publisher = SnsTopicPublisher(topic_arn=TOPIC_ARN, sns_client=mock_sns_client)

    message = "Some plain text"
    expected_formatted_message = message
    subject = "test-subject"

    sns_publisher.publish_message(message=message, subject=subject)

    mock_sns_client.publish.assert_called_with(
        TopicArn=TOPIC_ARN, Message=expected_formatted_message, Subject=subject
    )


def test_explicit_client(aws_sns_client):
    aws_sns_client.create_topic(Name=TOPIC_NAME)

    sns_publisher = SnsTopicPublisher(topic_arn=TOPIC_ARN, sns_client=aws_sns_client)

    message = "Some plain text"
    expected_formatted_message = message

    with patch.object(
        aws_sns_client, "publish", wraps=aws_sns_client.publish
    ) as mock_publish:
        sns_publisher.publish_message(message=message)

        # Assert that the publish method was called with the expected parameters
        mock_publish.assert_called_with(
            TopicArn=TOPIC_ARN,
            Message=expected_formatted_message,
        )


def test_failed_publish(aws_sns_client):
    aws_sns_client.create_topic(Name="very-wrong-topic")

    # topic doesn't exist as we created a wrong one
    sns_publisher = SnsTopicPublisher(topic_arn=TOPIC_ARN, sns_client=aws_sns_client)

    message = "Some plain text"

    with pytest.raises(SNSTopicPublisherException, match="Endpoint does not exist"):
        sns_publisher.publish_message(message=message)
