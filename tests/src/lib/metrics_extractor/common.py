from lib.aws import Boto3ClientCreator
import pytest


####################################################################

@pytest.fixture(scope="module")
def boto3_client_creator():
    return Boto3ClientCreator("1234567890", "us-east-1")


####################################################################


def contains_required_items(record, ts_record_subkey, required_items):
    record_items = [x["Name"] for x in record[ts_record_subkey]]
    for dimension in required_items:
        if dimension not in record_items:
            return False

    return True

def get_dimension_value(record, dimension_name):
    dim_data = record["Dimensions"]
    for dim_entry in dim_data:
        if dim_entry["Name"] == dimension_name:
            return dim_entry["Value"]

    return None

def get_measure_value(record, metric_name):
    measure_data = record["MeasureValues"]
    for measure in measure_data:
        if measure["Name"] == metric_name:
            return measure["Value"]

    return None
