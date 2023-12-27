from datetime import datetime
import time


def epoch_milliseconds(epoch_seconds: float = None) -> int:
    """
    Converts epoch time in seconds to a int representation in milliseconds.

    If no argument is provided, the current time is used.

    Args:
        epoch_seconds (float, optional): The epoch time in seconds. If None,
                                         the current time is used. Defaults to None.

    Returns:
        str: The epoch time in milliseconds as an int.
    """
    tmp = epoch_seconds if epoch_seconds is not None else time.time()
    return int(round(tmp * 1000))


def datetime_to_epoch_milliseconds(datetime_value: datetime) -> str:
    """
    Convert a datetime object to a string representation in milliseconds (which is required to timestream record)

    Parameters:
    datetime_value (datetime): The datetime object to be converted.

    Returns:
    str: The datetime object as a string in milliseconds.
    """
    return str(epoch_milliseconds(datetime_value.timestamp()))


def iso_time_to_epoch_milliseconds(iso_date: str) -> int:
    """
    Convert an ISO 8601 formatted date string to the number of milliseconds since the Unix epoch.
    If the input is None, the current time in milliseconds since the Unix epoch is returned.

    Parameters:
    iso_date (str): An ISO 8601 formatted date string (e.g., "2023-11-21T21:39:09Z").
                    If None, the current time is used.

    Returns:
    str: The number of milliseconds since the Unix epoch as a string.
    """

    # If the input is None, use the current time
    if iso_date is None:
        return epoch_milliseconds()
    else:
        # Convert the ISO date string to a datetime object
        dt = datetime.fromisoformat(iso_date.rstrip("Z"))
        # Convert the datetime object to epoch time in seconds
        epoch_time = dt.timestamp()
        return epoch_milliseconds(epoch_time)
