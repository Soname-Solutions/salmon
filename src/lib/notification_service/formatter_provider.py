from .formatter import HtmlFormatter


class FormatterProvider:
    """Formatter factory."""

    def __init__(self):
        self._formatters = {}

    def register_sender(self, delivery_method, sender):
        self._formatters[delivery_method] = sender

    def get(self, delivery_method):
        formatter = self._formatters.get(delivery_method)

        if not formatter:
            raise ValueError(f"Delivery method {delivery_method} is not supported.")

        return formatter()


formatters = FormatterProvider()
formatters.register_sender("AWS_SES", HtmlFormatter)
formatters.register_sender("SMTP", HtmlFormatter)
