from unittest.mock import patch

from lib.aws.ses_manager import AwsSesRawEmailSenderException
from lib.notification_service.sender import AwsSesSender, AwsSesNoRelevantRecipientsException, AwsSesSenderException, AwsSesUserNotVerifiedException
from lib.notification_service.messages import Message, File
import pytest


def test_send():
    delivery_method = { "name" : "sns_test", "delivery_method_type" : "AWS_SES" }
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com", "email2@company.com"]

    with patch("lib.notification_service.sender.ses.AwsSesManager") as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = recipients
       
        sender = AwsSesSender(delivery_method=delivery_method, message=message, recipients=recipients)
        sender.pre_process()
        sender.send()

        # no return values from function, so we are testing successful completion only

def test_send_with_file():
    delivery_method = { "name" : "sns_test", "delivery_method_type" : "AWS_SES" }
    message = Message(subject="test", body="test", file=File(name="attach.txt", content="test content"))
    recipients = ["email1@company.com", "email2@company.com"]

    with patch("lib.notification_service.sender.ses.AwsSesManager") as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = recipients
       
        sender = AwsSesSender(delivery_method=delivery_method, message=message, recipients=recipients)
        sender.pre_process()
        sender.send()    

        # no return values from function, so we are testing successful completion only

def test_unverified_recipient():
    delivery_method = { "name" : "sns_test", "delivery_method_type" : "AWS_SES" }
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com", "email2@company.com"]

    with patch("lib.notification_service.sender.ses.AwsSesManager") as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = ["email1@company.com"]
       
        with pytest.raises(AwsSesUserNotVerifiedException, match="email2@company.com are not verified in SES"):
            sender = AwsSesSender(delivery_method=delivery_method, message=message, recipients=recipients)
            sender.pre_process()
            sender.send()            

def test_no_recipients():
    delivery_method = { "name" : "sns_test", "delivery_method_type" : "AWS_SES" }
    message = Message(subject="test", body="test")
    recipients = []

    with patch("lib.notification_service.sender.ses.AwsSesManager") as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = ["email1@company.com"]
       
        with pytest.raises(AwsSesNoRelevantRecipientsException):
            sender = AwsSesSender(delivery_method=delivery_method, message=message, recipients=recipients)
            sender.pre_process()
            sender.send()                

def test_error_while_sending():
    delivery_method = { "name" : "sns_test", "delivery_method_type" : "AWS_SES" }
    message = Message(subject="test", body="test")
    recipients = ["email1@company.com"]

    with patch("lib.notification_service.sender.ses.AwsSesManager") as MockAwsSesManager:
        mock_ses_manager_instance = MockAwsSesManager.return_value
        mock_ses_manager_instance.get_verified_identities.return_value = ["email1@company.com"]
        mock_ses_manager_instance.send_raw_email.side_effect = AwsSesRawEmailSenderException("test exception")
       
        with pytest.raises(AwsSesSenderException):
            sender = AwsSesSender(delivery_method=delivery_method, message=message, recipients=recipients)
            sender.pre_process()
            sender.send()    

    