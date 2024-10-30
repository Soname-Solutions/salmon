from lib.notification_service.sender import AwsSnsSender, AwsSnsSenderException
from lib.notification_service.messages import Message
import pytest
from unittest.mock import patch

ACCOUNT_ID = "123456789012"
REGION_NAME = "us-east-1"
TOPIC_NAME = "fake-topic"
TOPIC_ARN = f"arn:aws:sns:{REGION_NAME}:{ACCOUNT_ID}:{TOPIC_NAME}"


def test1():
    delivery_method = {"name": "sns_test", "delivery_method_type": "AWS_SES"}
    message = Message(subject="test", body="test")
    recipients = [TOPIC_ARN]

    with patch(
        "lib.notification_service.sender.aws_sns_sender.SnsTopicPublisher"
    ) as MockAwsSnsManager:
        sender = AwsSnsSender(
            delivery_method=delivery_method, message=message, recipients=recipients
        )
        sender.pre_process()
        sender.send()


def test_exception_while_sending():
    delivery_method = {"name": "sns_test", "delivery_method_type": "AWS_SES"}
    message = Message(subject="test", body="test")
    recipients = [TOPIC_ARN]

    # here we don't mock SnsTopicPublisher, so it actually tries to publsh to fake-topic and fails
    with pytest.raises(AwsSnsSenderException):
        sender = AwsSnsSender(
            delivery_method=delivery_method, message=message, recipients=recipients
        )
        sender.pre_process()
        sender.send()
