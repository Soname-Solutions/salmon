from .sender import create_aws_ses_sender


class SenderProvider:
    def __init__(self):
        self._senders = {}
    
    def register_sender(self, delivery_method, sender):
        self._senders[delivery_method] = sender
    
    def get(self, delivery_method, **kwargs):
        sender = self._senders.get(delivery_method)

        if not sender:
            raise ValueError(f"Delivery method {delivery_method} is not supported.")
        
        return sender(**kwargs)


senders = SenderProvider()
senders.register_sender("AWS_SES", create_aws_ses_sender)
