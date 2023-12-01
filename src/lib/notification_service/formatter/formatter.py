from abc import ABC, abstractmethod


class Formatter(ABC):
    @property
    def _available_methods(self):
        """All available methods to apply during formatting."""
        return {"text": self.get_text, "table": self.get_table}

    # @staticmethod
    def format(self, object_type: str, **kwargs):
        """Get a method based on an object type."""
        method = self._available_methods.get(object_type)

        if not method:
            raise ValueError(f"Message object type {object_type} is not supported.")

        return method(**kwargs)

    @abstractmethod
    def get_text(self) -> None:
        """Get a text."""
        pass

    @abstractmethod
    def get_table(self) -> None:
        """Get a header."""
        pass
