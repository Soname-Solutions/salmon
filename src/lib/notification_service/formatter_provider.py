from .formatter import BaseFormatter, HtmlFormatter, PlainTextFormatter
from lib.core.constants import DeliveryMethodTypes
from lib.settings.settings_classes import DeliveryMethod


class FormatterProvider:
    """Formatter factory."""

    def __init__(self):
        self._formatters = {}

    def register_formatter(self, delivery_method_type: str, formatter):
        self._formatters[delivery_method_type] = formatter

    def get(self, delivery_method: DeliveryMethod) -> BaseFormatter:
        formatter = self._formatters.get(delivery_method.delivery_method_type)

        if not formatter:
            raise ValueError(
                f"Delivery method {delivery_method.delivery_method_type} is not supported."
            )

        return formatter(delivery_method)


formatters = FormatterProvider()
formatters.register_formatter(DeliveryMethodTypes.AWS_SES, HtmlFormatter)
formatters.register_formatter(DeliveryMethodTypes.AWS_SNS, PlainTextFormatter)
formatters.register_formatter(DeliveryMethodTypes.SMTP, HtmlFormatter)
