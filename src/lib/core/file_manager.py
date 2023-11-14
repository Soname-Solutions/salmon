import os


class FileManagerReadException(Exception):
    """Exception raised for errors during file reading in the FileManager class."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FileManagerWriteException(Exception):
    """Exception raised for errors during file writing in the FileManager class."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FileManager:
    """Manages reading and writing text files from/to a specified base path.

    This class provides methods for reading and writing text files, and it handles exceptions
    specific to file reading and writing operations.

    Attributes:
        base_path (str): The base path for file interactions.

    Methods:
        read_file: Reads the content of a text file.
        write_file: Writes data to a text file.

    """

    def __init__(self, base_path: str = "."):
        """FileManager class constructor.

        Args:
            base_path (str, optional): The base path for file interactions. Defaults to '.'.
        """
        self.base_path = base_path

    def _get_full_path(self, file_path: str) -> str:
        """Gets the full path by combining the base path and the file path.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The full path.
        """
        return os.path.join(self.base_path, file_path)

    def read_file(self, file_path: str) -> str:
        """Reads the content of a text file.

        Args:
            file_path (str): The path to the text file.

        Returns:
            str: The content of the text file.

        Raises:
            FileManagerReadException: If an error occurs during file reading.
        """
        full_path = self._get_full_path(file_path)
        try:
            with open(full_path, "r") as file:
                return file.read()
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {full_path}") from e
        except Exception as e:
            error_message = f"Error reading file '{full_path}': {e}"
            raise FileManagerReadException(error_message)

    def write_file(self, file_path: str, data: str):
        """Writes data to a text file.

        Args:
            file_path (str): The path to the text file.
            data (str): The data to be written to the text file.

        Raises:
            FileManagerWriteException: If an error occurs during file writing.
        """
        full_path = self._get_full_path(file_path)
        try:
            with open(full_path, "w") as file:
                file.write(data)
        except Exception as e:
            error_message = f"Error writing file '{full_path}': {e}"
            raise FileManagerWriteException(error_message)
