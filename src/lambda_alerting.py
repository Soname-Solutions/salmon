import os
import json
import boto3
import logging

from lib.core import time_utils
from lib.aws.sqs_manager import SQSQueueSender
from lib.aws.cloudwatch_manager import CloudWatchEventsPublisher
from lib.event_mapper.aws_event_mapper import AwsEventMapper
from lib.settings import Settings

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client("sqs")
cloudwatch_client = boto3.client("logs")


def write_event_to_cloudwatch(
    monitored_env_name: str,
    resource_name: str,
    service_name: str,
    event_severity: str,
    event: dict,
):
    """
    Writes a given list of records to an Amazon CloudWatch logs.

    Retrieves the log group and log stream names from environment variables and uses
    an instance of CloudWatchEventPublisher to write the provided records to the
    specified CloudWatch log stream.

    Args:
        monitored_env_name (str): The name of the monitored environment.
        resource_name (str): The name of the AWS resource.
        service_name (str): The name of the AWS service.
        event_severity (str): Severity of the event.
        event (dict): The event dict to be written to the CloudWatch stream.

    Returns:
        None: This function does not return anything but logs the outcome.
    """
    log_group_name = os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME"]
    log_stream_name = os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME"]

    publisher = CloudWatchEventsPublisher(
        log_group_name=log_group_name,
        log_stream_name=log_stream_name,
        cloudwatch_client=cloudwatch_client,
    )

    logged_event = {}
    logged_event["event"] = event
    logged_event["monitored_environment"] = monitored_env_name
    logged_event["resource_name"] = resource_name
    logged_event["service_name"] = service_name
    logged_event["event_severity"] = event_severity

    logged_event_time = time_utils.iso_time_to_epoch_milliseconds(event["time"])
    result = publisher.put_event(logged_event_time, json.dumps(logged_event, indent=4))

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


def lambda_handler(event, context):
    logger.info(f"event = {event}")

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    settings = Settings.from_s3_path(settings_s3_path)

    monitored_env_name = settings.get_monitored_environment_name(
        event["account"], event["region"]
    )

    mapper = AwsEventMapper(settings)
    messages = mapper.to_notification_messages(event)

    logger.info(f"Notification messages: {messages}")

    queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
    send_messages_to_sqs(queue_url, messages)

    resource_name = mapper.to_resource_name(event)
    service_name = mapper.to_service_name(event)
    event_severity = mapper.to_event_severity(event)
    write_event_to_cloudwatch(
        monitored_env_name, resource_name, service_name, event_severity, event
    )

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
