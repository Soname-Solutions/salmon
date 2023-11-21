import os
import json
import boto3

from lib.aws.timestream_manager import (
    iso_time_to_epoch_milliseconds,
    TimestreamTableWriter,
)

timestream_write_client = boto3.client("timestream-write")


def write_event_to_timestream(records):
    db_name = os.environ["ALERT_EVENTS_DB_NAME"]
    table_name = os.environ["ALERT_EVENTS_TABLE_NAME"]

    writer = TimestreamTableWriter(
        db_name=db_name,
        table_name=table_name,
        timestream_write_client=timestream_write_client,
    )
    result = writer.write_records(records=records)

    print("EventJSON has been written successfully")
    print(result)


def settings_stub_get_monitored_env_name(account, region):
    return "monitored_env_from_stub"


def parse_event_properties(event):
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
    records = []

    dimensions = [
        {
            "Name": "Monitored_Environment",
            "Value": event_props["monitored_environment"],
        },
        {"Name": "Source", "Value": event_props["source"]},
    ]
    record_time = iso_time_to_epoch_milliseconds(event_props["time"])

    records.append(
        {
            "Dimensions": dimensions,
            "MeasureName": "EventJson",
            "MeasureValue": json.dumps(event, indent=4),
            "MeasureValueType": "VARCHAR",
            "Time": record_time,
        }
    )

    return records


def lambda_handler(event, context):
    print(f"event = {event}")

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
