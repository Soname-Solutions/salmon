from .formatter import HtmlFormatter, PlainTextFormatter
from lib.core.constants import DeliveryMethodTypes


class FormatterProvider:
    """Formatter factory."""

    def __init__(self):
        self._formatters = {}

    def register_sender(self, delivery_method_type, sender):
        self._formatters[delivery_method_type] = sender

    def get(self, delivery_method_type):
        formatter = self._formatters.get(delivery_method_type)

        if not formatter:
            raise ValueError(
                f"Delivery method {delivery_method_type} is not supported."
            )

        return formatter()


formatters = FormatterProvider()
formatters.register_sender(DeliveryMethodTypes.AWS_SES, HtmlFormatter)
formatters.register_sender(DeliveryMethodTypes.AWS_SNS, PlainTextFormatter)
formatters.register_sender(DeliveryMethodTypes.SMTP, HtmlFormatter)
