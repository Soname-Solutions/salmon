# Import the necessary libraries
import pytest
from datetime import datetime, timezone
from lib.core.datetime_utils import str_utc_datetime_to_datetime  

@pytest.fixture(params = [
    ("2024-02-05 07:46:42.335000000", datetime(2024, 2, 5, 7, 46, 42, 335000, tzinfo=timezone.utc)),
    # Datetime with fractional seconds (but 6 digits)
    ("2024-02-05 07:46:42.335000", datetime(2024, 2, 5, 7, 46, 42, 335000, tzinfo=timezone.utc)),    
    # Datetime with full fractional seconds ending in zeros
    ("2024-02-03 19:36:52.000000000", datetime(2024, 2, 3, 19, 36, 52, 0, tzinfo=timezone.utc)),    
])
def input_data(request):
    yield request.param
    
def test_str_utc_datetime_to_datetime_with_fixture(input_data):
    input_datetime_str, expected_datetime = input_data
    result = str_utc_datetime_to_datetime(input_datetime_str)
    print(result)
    print(expected_datetime)
    assert result == expected_datetime, "The converted datetime does not match the expected datetime."    


# Test to ensure the function assigns UTC timezone correctly
def test_utc_timezone_assignment():
    input_datetime_str = "2024-02-03 19:36:52.123000000"
    result = str_utc_datetime_to_datetime(input_datetime_str)
    assert result.tzinfo is not None and result.tzinfo == timezone.utc, "The timezone is not correctly assigned as UTC."
