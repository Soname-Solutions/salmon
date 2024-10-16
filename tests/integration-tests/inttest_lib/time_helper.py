from datetime import datetime, timezone, timedelta
import time


def epoch_to_utc_string(epoch_ms):
    # Convert epoch milliseconds to seconds
    epoch_sec = epoch_ms / 1000.0
    dt = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
    return dt.isoformat()


def utc_string_to_epoch(utc_string):
    # Parse the UTC time string into a datetime object
    dt = datetime.fromisoformat(utc_string)
    epoch_ms = int(dt.timestamp() * 1000)
    return epoch_ms


def epoch_seconds_to_utc_datetime(epoch_seconds: int) -> datetime:
    # Get the local timezone offset in seconds
    offset_seconds = -time.timezone if time.localtime().tm_isdst == 0 else -time.altzone
    offset = timedelta(seconds=offset_seconds)

    # Convert epoch_seconds to a datetime in the local timezone
    local_datetime = datetime.fromtimestamp(epoch_seconds, tz=timezone(offset))

    # Convert the local datetime to UTC
    utc_datetime = local_datetime.astimezone(timezone.utc)
    return utc_datetime
