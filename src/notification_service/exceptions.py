class SenderException(Exception):
    """Error while sending a message."""
    pass


class AwsSesSenderException(SenderException):
    """Error while sending a message via AWS SES."""
    pass


class AwsSesUserNotVerifiedException(Exception):
    """AWS SES user is not verified."""
    pass


class AwsSesNoRelevantRecipientsException(Exception):
    """No relevant recipients to send a message to in AWS SES."""
    pass
