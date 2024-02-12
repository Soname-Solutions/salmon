from .sender import create_aws_ses_sender, create_smtp_sender


class SenderProvider:
    """Sender factory."""

    def __init__(self):
        self._senders = {}

    def register_sender(self, delivery_method_type, sender):
        self._senders[delivery_method_type] = sender

    def get(self, delivery_method_type, **kwargs):
        sender = self._senders.get(delivery_method_type)

        if not sender:
            raise ValueError(
                f"Delivery method {delivery_method_type} is not supported."
            )

        return sender(**kwargs)


senders = SenderProvider()
senders.register_sender("AWS_SES", create_aws_ses_sender)
senders.register_sender("SMTP", create_smtp_sender)
