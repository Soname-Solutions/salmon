import os
import json
import boto3
import logging

from lib.aws.sqs_manager import SQSQueueSender
from lib.aws.timestream_manager import TimestreamTableWriter
from lib.event_mapper.aws_event_mapper import AwsEventMapper
from lib.core import json_utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

timestream_write_client = boto3.client("timestream-write")
sqs_client = boto3.client("sqs")
# TODO: import settingss


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


def read_settings(s3_bucket_name):
    settings_path = f"s3://{s3_bucket_name}/settings"
    settings = {}  # TODO: replace with real settings call
    # settings = Settings.from_s3_path(settings_path)
    return settings


def send_messages_to_sqs(queue_url, messages):
    sender = SQSQueueSender(queue_url, sqs_client)
    results = sender.send_messages(messages)

    logger.info("Messages have been sent successfully to SQS")
    logger.info(results)


def parse_event_properties(event, settings):
    """
    Extracts and structures properties from the given event.

    Parses an event to extract its source, account ID, region, and time, and
    assigns a monitored environment name to it using a stub function.

    Args:
        event (dict): The event data in dictionary format.

    Returns:
        dict: A dictionary containing structured event properties.
    """
    outp = json_utils.parse_json(event)
    return outp


def get_monitored_env_name(event, settings):
    # return settings.get_monitored_environment_name(event["account_id"], event["region"])
    return "monitored_env_from_stub"  # TODO: replace with real settings call


def prepare_timestream_record(event_props, monitored_env_name, event):
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
            "Value": monitored_env_name,
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


def map_to_notification_messages(event_props, settings):
    mapper = AwsEventMapper(settings)
    messages = mapper.to_notification_messages(event_props)

    return messages


def lambda_handler(event, context):
    logger.info(f"event = {event}")

    settings_bucket_name = os.environ("SETTINGS_S3_BUCKET_NAME")
    settings = read_settings(settings_bucket_name)

    event_props = parse_event_properties(event, settings)
    monitored_env_name = get_monitored_env_name(event, settings)

    # 1. parses event to identify "source" - e.g. "glue"
    # 2. Create instance of <source>AlertParser class and calls method "parse"
    # parse method returns DSL-markedup message
    messages = map_to_notification_messages(event_props, settings)

    # 3. asks settings module for
    # a) monitoring group item belongs to
    # b) list of relevant recipients and their delivery method

    # 3. for each recipient:
    # sends message to SQS queue (DSL-markup + recipient and delivery method info)

    print(messages)

    queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
    send_messages_to_sqs(queue_url, messages)

    # 4. writes event into timestream DB table named <<TBD>>
    # dimensions: a) monitoring group, b) service
    # metric = error message
    timestream_records = prepare_timestream_record(
        event_props, monitored_env_name, event
    )

    write_event_to_timestream(timestream_records)

    return {"messages": messages}


if __name__ == "__main__":
    # os vars passed when lambda is created
    os.environ[
        "ALERT_EVENTS_DB_NAME"
    ] = "timestream-salmon-metrics-events-storage-devvd"
    os.environ["NOTIFICATION_QUEUE_NAME"] = "queue-salmon-notification-devvd"
    os.environ["SETTINGS_S3_BUCKET_NAME"] = "s3-salmon-settings-devvd"
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
    glue_event = {
        "version": "0",
        "id": "abcdef00-1234-5678-9abc-def012345678",
        "detail-type": "Glue Job State Change",
        "source": "aws.glue",
        "account": "123456789012",
        "time": "2017-09-07T18:57:21Z",
        "region": "us-east-1",
        "resources": [],
        "detail": {
            "jobName": "MyJob",
            "severity": "INFO",
            "state": "SUCCEEDED",
            "jobRunId": "jr_abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            "message": "Job run succeeded",
        },
    }
    step_functions_event = {
        "version": "0",
        "id": "315c1398-40ff-a850-213b-158f73e60175",
        "detail-type": "Step Functions Execution Status Change",
        "source": "aws.states",
        "account": "123456789012",
        "time": "2019-02-26T19:42:21Z",
        "region": "us-east-1",
        "resources": [
            "arn:aws:states:us-east-1:123456789012:execution:state-machine-name:execution-name"
        ],
        "detail": {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:state-machine-name:execution-name",
            "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:state-machine",
            "name": "execution-name",
            "status": "FAILED",
            "startDate": 1551225146847,
            "stopDate": 1551225151881,
            "input": "{}",
            "output": "null",
        },
    }
    context = None
    lambda_handler(glue_event, context)
