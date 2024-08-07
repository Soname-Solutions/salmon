from datetime import datetime, timezone

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

