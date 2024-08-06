from datetime import datetime, timezone

def epoch_to_utc_string(epoch_ms):
    # Convert epoch milliseconds to seconds
    epoch_sec = epoch_ms / 1000.0
    # Create a datetime object from the epoch time
    dt = datetime.fromtimestamp(epoch_sec, tz=timezone.utc)
    # Return the formatted string with timezone info
    return dt.isoformat()

# Example usage
# epoch_ms = 1609459200000  # This represents 2021-01-01 00:00:00 UTC
# utc_string = epoch_to_utc_string(epoch_ms)
# print(utc_string)  # Output: 2021-01-01T00:00:00+00:00

def utc_string_to_epoch(utc_string):
    # Parse the UTC time string into a datetime object
    dt = datetime.fromisoformat(utc_string)
    # Get the epoch time in seconds and convert to milliseconds
    epoch_ms = int(dt.timestamp() * 1000)
    return epoch_ms

# # Example usage
# utc_string = "2021-01-01T00:00:00+00:00"
# epoch_ms = utc_string_to_epoch(utc_string)
# print(epoch_ms)  # Output: 1609459200000