import pytest
from unittest.mock import patch
from smtplib import SMTPResponseException

from lib.aws.secret_manager import SecretManager
from lib.core.constants import DeliveryMethodTypes
from lib.notification_service.sender import SmtpSender
from lib.notification_service.messages import Message, File
from lib.notification_service.exceptions import SmtpSenderException
from lib.settings.settings_classes import DeliveryMethod

TEST_SECRET_NAME = "test-smtp-server-creds"
TEST_SECRET = {
    "SMTP_SERVER": "test_server",
    "SMTP_PORT": 111,
    "SMTP_LOGIN": "test_login",
    "SMTP_PASSWORD": "test_password",
}
TEST_RECIPIENTS = ["email1@company.com", "email2@company.com"]
TEST_MSG_SUBJECT = "test_subject"
TEST_MSG_BODY = "test_message_body"


@pytest.fixture
def smtp_delivery_method():
    return DeliveryMethod(
        name="smtp",
        delivery_method_type=DeliveryMethodTypes.SMTP,
        sender_email="no-reply@company.com",
        credentials_secret_name=TEST_SECRET_NAME,
        # assuming use_ssl = True, timeout = 10.0 - default from settings_classes.DeliveryMethod
    )


@patch.object(SecretManager, "get_secret", return_value=TEST_SECRET)
@patch("lib.notification_service.sender.smtp_sender.SMTP_SSL")
@patch("ssl.create_default_context")
def test_smtp_send_via_ssl(
    mock_ssl_context, mock_smtp_ssl, mock_get_secret, smtp_delivery_method
):
    # by default, SSL enabled
    # mock the SSL context, SMTP_SSL instance
    mock_ssl_instance = mock_ssl_context.return_value
    mock_smtp_server_instance = mock_smtp_ssl.return_value.__enter__.return_value

    message = Message(subject=TEST_MSG_SUBJECT, body=TEST_MSG_BODY)
    sender = SmtpSender(
        delivery_method=smtp_delivery_method,
        message=message,
        recipients=TEST_RECIPIENTS,
    )
    sender.pre_process()
    sender.send()
    # no return values from function, so we are testing successful completion only

    # assert get_secret call
    mock_get_secret.assert_called_once_with(
        secret_name=smtp_delivery_method.credentials_secret_name
    )
    # assert SMTP_SSL call
    mock_smtp_ssl.assert_called_once_with(
        host=TEST_SECRET["SMTP_SERVER"],
        port=TEST_SECRET["SMTP_PORT"],
        timeout=10.0,
        context=mock_ssl_instance,
    )
    # assert SMTP_SSL login call
    mock_smtp_server_instance.login.assert_called_once_with(
        user=TEST_SECRET["SMTP_LOGIN"], password=TEST_SECRET["SMTP_PASSWORD"]
    )
    # assert SMTP_SSL sendmail call
    sendmail_args = mock_smtp_server_instance.sendmail.call_args[1]
    assert sendmail_args["from_addr"] == smtp_delivery_method.sender_email
    assert sendmail_args["to_addrs"] == TEST_RECIPIENTS
    assert f"Subject: {TEST_MSG_SUBJECT}" in sendmail_args["msg"]


@patch.object(SecretManager, "get_secret", return_value=TEST_SECRET)
@patch("lib.notification_service.sender.smtp_sender.SMTP")
@patch("ssl.create_default_context")
def test_smtp_send_via_starttls(
    mock_starttls_context, mock_smtp_starttls, mock_get_secret, smtp_delivery_method
):
    # SSL disabled, so STARTTLS will be used
    smtp_delivery_method.use_ssl = False

    # mock the SSL context, SMTP instance
    mock_starttls_instance = mock_starttls_context.return_value
    mock_smtp_server_instance = mock_smtp_starttls.return_value.__enter__.return_value

    message = Message(subject=TEST_MSG_SUBJECT, body=TEST_MSG_BODY)
    sender = SmtpSender(
        delivery_method=smtp_delivery_method,
        message=message,
        recipients=TEST_RECIPIENTS,
    )
    sender.pre_process()
    sender.send()
    # no return values from function, so we are testing successful completion only

    # assert get_secret call
    mock_get_secret.assert_called_once_with(
        secret_name=smtp_delivery_method.credentials_secret_name
    )
    # assert SMTP call
    mock_smtp_starttls.assert_called_once_with(
        host=TEST_SECRET["SMTP_SERVER"],
        port=TEST_SECRET["SMTP_PORT"],
        timeout=10.0,
    )
    # assert SMTP starttls call
    mock_smtp_server_instance.starttls.assert_called_once_with(
        context=mock_starttls_instance
    ),
    # assert SMTP login call
    mock_smtp_server_instance.login.assert_called_once_with(
        user=TEST_SECRET["SMTP_LOGIN"], password=TEST_SECRET["SMTP_PASSWORD"]
    )
    # assert SMTP sendmail call
    sendmail_args = mock_smtp_server_instance.sendmail.call_args[1]
    assert sendmail_args["from_addr"] == smtp_delivery_method.sender_email
    assert sendmail_args["to_addrs"] == TEST_RECIPIENTS
    assert f"Subject: {TEST_MSG_SUBJECT}" in sendmail_args["msg"]


@patch.object(SecretManager, "get_secret", return_value=TEST_SECRET)
@patch("lib.notification_service.sender.smtp_sender.SMTP_SSL")
@patch("ssl.create_default_context")
def test_smtp_send_with_file(
    mock_starttls_context, mock_smtp_starttls, mock_get_secret, smtp_delivery_method
):
    message = Message(
        subject=TEST_MSG_SUBJECT,
        body=TEST_MSG_BODY,
        file=File(name="attach.txt", content="test content"),
    )
    sender = SmtpSender(
        delivery_method=smtp_delivery_method,
        message=message,
        recipients=TEST_RECIPIENTS,
    )
    sender.pre_process()
    sender.send()
    # no return values from function, so we are testing successful completion only


@patch.object(SecretManager, "get_secret", return_value=TEST_SECRET)
@patch("lib.notification_service.sender.smtp_sender.SMTP_SSL")
@patch("ssl.create_default_context")
def test_smtp_error_while_sending(
    mock_starttls_context, mock_smtp_starttls, mock_get_secret, smtp_delivery_method
):
    mock_smtp_server_instance = mock_smtp_starttls.return_value.__enter__.return_value
    mock_smtp_server_instance.sendmail.side_effect = SMTPResponseException(
        code=111, msg="test exception"
    )

    message = Message(subject=TEST_MSG_SUBJECT, body=TEST_MSG_BODY)
    sender = SmtpSender(
        delivery_method=smtp_delivery_method,
        message=message,
        recipients=TEST_RECIPIENTS,
    )
    with pytest.raises(SmtpSenderException):
        sender.pre_process()
        sender.send()


@patch.object(SecretManager, "get_secret", return_value=TEST_SECRET)
@patch("lib.notification_service.sender.smtp_sender.SMTP")
@patch("ssl.create_default_context")
def test_smtp_sender_key_error(
    mock_starttls_context, mock_smtp_starttls, mock_get_secret, smtp_delivery_method
):
    message = Message(subject=TEST_MSG_SUBJECT, body=TEST_MSG_BODY)
    sender = SmtpSender(
        delivery_method=smtp_delivery_method,
        message=message,
        recipients=TEST_RECIPIENTS,
    )
    TEST_SECRET["SMTP_PORT"] = None
    with pytest.raises(
        KeyError, match="SMTP property SMTP_PORT is not defined in the secret"
    ):
        sender.pre_process()
        sender.send()

    smtp_delivery_method.credentials_secret_name = None
    with pytest.raises(KeyError, match="Credentials Secret Name is not set."):
        sender.pre_process()
        sender.send()


def test_error_empty_sender_email():
    # sender_email field is omitted
    ses_delivery_method = DeliveryMethod(
        name="smtp",
        delivery_method_type=DeliveryMethodTypes.SMTP,
        credentials_secret_name=TEST_SECRET_NAME,
    )

    message = "some text"
    recipients = []

    with pytest.raises(SmtpSenderException):
        sender = SmtpSender(
            delivery_method=ses_delivery_method, message=message, recipients=recipients
        )


def test_error_no_credentials_secret_name():
    # credentials_secret_name field is omitted
    ses_delivery_method = DeliveryMethod(
        name="smtp",
        delivery_method_type=DeliveryMethodTypes.SMTP,
        sender_email="no-reply@company.com",
    )

    message = "some text"
    recipients = []

    with pytest.raises(SmtpSenderException):
        sender = SmtpSender(
            delivery_method=ses_delivery_method, message=message, recipients=recipients
        )
