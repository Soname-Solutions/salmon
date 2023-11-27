from abc import ABC, abstractmethod


class Formatter(ABC):
    @abstractmethod
    def get_header(self) -> None:
        """Get a header."""
        pass

    @abstractmethod
    def get_table(self) -> None:
        """Get a header."""
        pass
