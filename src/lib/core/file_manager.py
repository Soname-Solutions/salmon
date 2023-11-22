# Exceptions
class FileManagerReadException(Exception):
    """Exception raised for errors during file reading."""

    pass


class FileManagerWriteException(Exception):
    """Exception raised for errors during file writing."""

    pass


# Functions
def read_file(file_path: str) -> str:
    """Reads the content of a text file.

    Args:
        file_path (str): The path to the text file.

    Returns:
        str: The content of the text file.

    Raises:
        FileManagerReadException: If an error occurs during file reading.

    """
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except Exception as e:
        error_message = f"Error reading file '{file_path}': {e}"
        raise FileManagerReadException(error_message)


def write_file(file_path: str, data: str):
    """Writes data to a text file.

    Args:
        file_path (str): The path to the text file.
        data (str): The data to be written to the text file.

    Raises:
        FileManagerWriteException: If an error occurs during file writing.

    """
    try:
        with open(file_path, "w") as file:
            file.write(data)
    except Exception as e:
        error_message = f"Error writing file '{file_path}': {e}"
        raise FileManagerWriteException(error_message)
