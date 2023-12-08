import os
import json
import boto3
import logging

from lib.aws.sqs_manager import SQSQueueSender
from lib.aws.timestream_manager import TimestreamTableWriter
from lib.event_mapper.aws_event_mapper import AwsEventMapper
from lib.settings import Settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

timestream_write_client = boto3.client("timestream-write")
sqs_client = boto3.client("sqs")


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


def send_messages_to_sqs(queue_url: str, messages: list[dict]):
    """Sends messages array to the given SQS queue

    Args:
        queue_url (str): SQS queue URL
        messages (list[dict]): list of message objects
    """
    sender = SQSQueueSender(queue_url, sqs_client)
    results = sender.send_messages(messages)

    logger.info(f"Results of sending messages to SQS: {results}")


def prepare_timestream_record(monitored_env_name, event):
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
        {"Name": "source", "Value": event["source"]},
    ]
    record_time = TimestreamTableWriter.iso_time_to_epoch_milliseconds(event["time"])

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


def map_to_notification_messages(event_props: dict, settings: Settings) -> list[dict]:
    """Maps given event object to notification messages array

    Args:
        event_props (dict): Event object
        settings (Settings): Settings object

    Returns:
        list[dict]: List of message objects
    """
    mapper = AwsEventMapper(settings)
    messages = mapper.to_notification_messages(event_props)

    return messages


def lambda_handler(event, context):
    logger.info(f"event = {event}")

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    settings = Settings.from_s3_path(settings_s3_path)

    monitored_env_name = settings.get_monitored_environment_name(
        event["account"], event["region"]
    )

    messages = map_to_notification_messages(event, settings)
    logger.info(f"Notification messages: {messages}")

    queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
    send_messages_to_sqs(queue_url, messages)

    timestream_records = prepare_timestream_record(monitored_env_name, event)
    write_event_to_timestream(timestream_records)

    return {"messages": messages}


if __name__ == "__main__":
    # os vars passed when lambda is created
    os.environ[
        "ALERT_EVENTS_DB_NAME"
    ] = "timestream-salmon-metrics-events-storage-devvd"
    os.environ[
        "NOTIFICATION_QUEUE_URL"
    ] = "https://sqs.eu-central-1.amazonaws.com/405389362913/queue-salmon-notification-devvd"
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devvd/settings/"
    os.environ["ALERT_EVENTS_TABLE_NAME"] = "alert-events"
    event = {
        "version": "0",
        "id": "cc90c8c7-57a6-f950-2248-c4c8db98a5ef",
        "detail-type": "test_event",
        "source": "awssoname.test777",
        "account": "405389362913",
        "time": "2023-11-28T21:55:03Z",
        "region": "eu-central-1",
        "resources": [],
        "detail": {"reason": "test777"},
    }

    glue_event = {
        "version": "0",
        "id": "abcdef00-1234-5678-9abc-def012345678",
        "detail-type": "Glue Job State Change",
        "source": "aws.glue",
        "account": "405389362913",
        "time": "2023-11-28T18:57:21Z",
        "region": "eu-central-1",
        "resources": [],
        "detail": {
            "jobName": "glue-salmonts-pyjob-1-dev",
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
        "account": "405389362913",
        "time": "2023-11-28T19:42:21Z",
        "region": "eu-central-1",
        "resources": [
            "arn:aws:states:us-east-1:123456789012:execution:state-machine-name:execution-name"
        ],
        "detail": {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:state-machine-name:execution-name",
            "stateMachineArn": "arn:aws:states:eu-central-1:405389362913:stateMachine:stepfunction-salmonts-sample-dev",
            "name": "execution-name",
            "status": "FAILED",
            "startDate": 1551225146847,
            "stopDate": 1551225151881,
            "input": "{}",
            "output": "null",
        },
    }

    context = None
    lambda_handler(step_functions_event, context)
