from abc import ABC, abstractmethod


class Formatter(ABC):
    @property
    def _available_methods(self):
        """All available methods to apply during formatting."""
        return {"text": self._get_text, "table": self._get_table}

    def _format(self, object_type: str, **kwargs):
        """Get a method based on an object type."""
        method = self._available_methods.get(object_type)

        if not method:
            raise ValueError(f"Message object type {object_type} is not supported.")

        return method(**kwargs)

    @abstractmethod
    def get_formatted_message(self, message_body: list) -> str:
        """Get final formatted message."""
        pass
