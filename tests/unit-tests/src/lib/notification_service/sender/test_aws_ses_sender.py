from unittest.mock import patch

from lib.aws.ses_manager import AwsSesRawEmailSenderException
from lib.notification_service.sender import (
    AwsSesSender,
    AwsSesNoRelevantRecipientsException,
    AwsSesSenderException,
    AwsSesUserNotVerifiedException,
)
from lib.notification_service.messages import Message, File
from lib.settings.settings_classes import DeliveryMethod
from lib.core.constants import DeliveryMethodTypes
import pytest


@pytest.fixture
def ses_delivery_method():
    return DeliveryMethod(
        name="ses_test",
        delivery_method_type=DeliveryMethodTypes.AWS_SES,
        sender_email="no-reply@company.com",
    )


def test_send(ses_delivery_method):
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com", "email2@company.com"]

    with patch(
        "lib.notification_service.sender.aws_ses_sender.AwsSesManager"
    ) as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = recipients

        sender = AwsSesSender(
            delivery_method=ses_delivery_method, message=message, recipients=recipients
        )
        sender.pre_process()
        sender.send()

        # no return values from function, so we are testing successful completion only


def test_send_with_file(ses_delivery_method):
    message = Message(
        subject="test",
        body="test",
        file=File(name="attach.txt", content="test content"),
    )
    recipients = ["email1@company.com", "email2@company.com"]

    with patch(
        "lib.notification_service.sender.aws_ses_sender.AwsSesManager"
    ) as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = recipients

        sender = AwsSesSender(
            delivery_method=ses_delivery_method, message=message, recipients=recipients
        )
        sender.pre_process()
        sender.send()

        # no return values from function, so we are testing successful completion only


def test_unverified_recipient(ses_delivery_method):
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com", "email2@company.com"]

    with patch(
        "lib.notification_service.sender.aws_ses_sender.AwsSesManager"
    ) as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = [
            "email1@company.com"
        ]

        with pytest.raises(
            AwsSesUserNotVerifiedException,
            match="email2@company.com are not verified in SES",
        ):
            sender = AwsSesSender(
                delivery_method=ses_delivery_method,
                message=message,
                recipients=recipients,
            )
            sender.pre_process()
            sender.send()


def test_no_recipients(ses_delivery_method):
    message = Message(subject="test", body="test")
    recipients = []

    with patch(
        "lib.notification_service.sender.aws_ses_sender.AwsSesManager"
    ) as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = [
            "email1@company.com"
        ]

        with pytest.raises(AwsSesNoRelevantRecipientsException):
            sender = AwsSesSender(
                delivery_method=ses_delivery_method,
                message=message,
                recipients=recipients,
            )
            sender.pre_process()
            sender.send()


def test_error_while_sending(ses_delivery_method):
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com"]

    with patch(
        "lib.notification_service.sender.aws_ses_sender.AwsSesManager"
    ) as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = [
            "email1@company.com"
        ]
        mock_ses_manager_instance.send_raw_email.side_effect = (
            AwsSesRawEmailSenderException("test exception")
        )

        with pytest.raises(AwsSesSenderException):
            sender = AwsSesSender(
                delivery_method=ses_delivery_method,
                message=message,
                recipients=recipients,
            )
            sender.pre_process()
            sender.send()


def test_error_empty_sender_email():
    # sender_email field is omitted
    ses_delivery_method = DeliveryMethod(
        name="ses_test", delivery_method_type=DeliveryMethodTypes.AWS_SES
    )

    message = "some text"
    recipients = []

    with pytest.raises(AwsSesSenderException):
        sender = AwsSesSender(
            delivery_method=ses_delivery_method, message=message, recipients=recipients
        )
