import os
import json
import boto3
import logging

from lib.aws.timestream_manager import TimestreamTableWriter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

timestream_write_client = boto3.client("timestream-write")


def write_event_to_timestream(records):
    """
    Writes a given list of records to an Amazon Timestream table.

    Retrieves the database and table names from environment variables and uses
    an instance of TimestreamTableWriter to write the provided records to the
    specified Timestream table.

    Args:
        records (list): A list of records to be written to the Timestream table.

    Returns:
        None: This function does not return anything but logs the outcome.
    """
    db_name = os.environ["ALERT_EVENTS_DB_NAME"]
    table_name = os.environ["ALERT_EVENTS_TABLE_NAME"]

    writer = TimestreamTableWriter(
        db_name=db_name,
        table_name=table_name,
        timestream_write_client=timestream_write_client,
    )
    result = writer.write_records(records=records)

    logger.info("EventJSON has been written successfully")
    logger.info(result)


def settings_stub_get_monitored_env_name(account, region):
    """
    A stub function to return a monitored environment name based on account and region.
    To be replaced when Settings Component is ready

    Args:
        account (str): AWS account ID.
        region (str): AWS region name.

    Returns:
        str: A string representing the name of the monitored environment.
    """
    return "monitored_env_from_stub"


def parse_event_properties(event):
    """
    Extracts and structures properties from the given event.

    Parses an event to extract its source, account ID, region, and time, and
    assigns a monitored environment name to it using a stub function.

    Args:
        event (dict): The event data in dictionary format.

    Returns:
        dict: A dictionary containing structured event properties.
    """
    outp = {
        "source": event.get("source", "Source Unknown"),
        "account_id": event.get("account", None),
        "region": event.get("region", None),
        "time": event.get("time", None),
    }
    outp["monitored_environment"] = settings_stub_get_monitored_env_name(
        outp["account_id"], outp["region"]
    )

    return outp


def prepare_timestream_record(event_props, event):
    """
    Prepares a Timestream record from the given event and its properties.

    Formats the event and its properties into the structure required by Timestream,
    including dimensions and time conversion.

    Args:
        event_props (dict): The structured properties of the event.
        event (dict): The original event data.

    Returns:
        list: A list containing the prepared Timestream record.
    """
    records = []

    dimensions = [
        {
            "Name": "monitored_environment",
            "Value": event_props["monitored_environment"],
        },
        {"Name": "source", "Value": event_props["source"]},
    ]
    record_time = TimestreamTableWriter.iso_time_to_epoch_milliseconds(event_props["time"])

    records.append(
        {
            "Dimensions": dimensions,
            "MeasureName": "event_json",
            "MeasureValue": json.dumps(event, indent=4),
            "MeasureValueType": "VARCHAR",
            "Time": record_time,
        }
    )

    return records


def lambda_handler(event, context):
    logger.info(f"event = {event}")

    event_props = parse_event_properties(event)

    # 1. parses event to identify "source" - e.g. "glue"

    # 2. Create instance of <source>AlertParser class and calls method "parse"
    # parse method returns DSL-markedup message

    # 3. asks settings module for
    # a) monitoring group item belongs to
    # b) list of relevant recipients and their delivery method

    # 3. for each recipient:
    # sends message to SQS queue (DSL-markup + recipient and delivery method info)

    # 4. writes event into timestream DB table named <<TBD>>
    # dimensions: a) monitoring group, b) service
    # metric = error message
    timestream_records = prepare_timestream_record(event_props, event)
    write_event_to_timestream(timestream_records)

    return {"event": event}


if __name__ == "__main__":
    # os vars passed when lambda is created
    os.environ[
        "ALERT_EVENTS_DB_NAME"
    ] = "timestream-salmon-metrics-events-storage-devam"
    os.environ["ALERT_EVENTS_TABLE_NAME"] = "alert-events"
    event = {
        "version": "0",
        "id": "cc90c8c7-57a6-f950-2248-c4c8db98a5ef",
        "detail-type": "test_event",
        "source": "awssoname.test777",
        "account": "405389362913",
        "time": "2023-11-21T21:55:03Z",
        "region": "eu-central-1",
        "resources": [],
        "detail": {"reason": "test777"},
    }
    context = None
    lambda_handler(event, context)
