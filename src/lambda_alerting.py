import os
import boto3
import logging

from lib.aws.sqs_manager import SQSQueueSender
from lib.event_mapper.event_mapper_provider import EventMapperProvider
from lib.event_mapper.resource_type_resolver import ResourceTypeResolver
from lib.settings import Settings
from lib.core.constants import EventResult
from lib.alerting_service import DeliveryOptionsResolver, CloudWatchAlertWriter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs_client = boto3.client("sqs")

EVENT_RESULTS_ALERTABLE = [EventResult.FAILURE]
EVENT_RESULTS_MONITORABLE = [EventResult.SUCCESS, EventResult.FAILURE]


def send_messages_to_sqs(queue_url: str, messages: list[dict]):
    """Sends messages array to the given SQS queue

    Args:
        queue_url (str): SQS queue URL
        messages (list[dict]): list of message objects
    """
    sender = SQSQueueSender(queue_url, sqs_client)
    results = sender.send_messages(messages)

    logger.info(f"Results of sending messages to SQS: {results}")


def map_to_notification_messages(message: dict, delivery_options: list) -> list:
    notification_messages = []

    for delivery_option in delivery_options:
        notification_message = {
            "delivery_options": delivery_option,
            "message": message,
        }
        notification_messages.append(notification_message)

    logger.info(f"Notification messages: {notification_messages}")

    return notification_messages


def lambda_handler(event, context):
    logger.info(f"event = {event}")

    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    settings = Settings.from_s3_path(settings_s3_path)

    resource_type = ResourceTypeResolver.resolve(event)
    mapper = EventMapperProvider.get_event_mapper(resource_type, event=event, settings=settings)

    event_result = mapper.get_event_result(event)
    resource_name = mapper.get_resource_name(event)
    event_status = mapper.get_resource_state(event)

    notification_messages = []

    if event_result in EVENT_RESULTS_ALERTABLE:
        message = mapper.to_message(event)
        delivery_options = DeliveryOptionsResolver.get_delivery_options(
            settings, resource_name
        )

        notification_messages = map_to_notification_messages(message, delivery_options)

        logger.info(f"Notification messages: {notification_messages}")

        queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
        send_messages_to_sqs(queue_url, notification_messages)
    else:
        logger.info(f"Event result is not alertable: {event_result}")

    if event_result in EVENT_RESULTS_MONITORABLE:
        log_group_name = os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME"]
        log_stream_name = os.environ["ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME"]
        CloudWatchAlertWriter.write_event_to_cloudwatch(
            log_group_name,
            log_stream_name,
            mapper.monitored_env_name,
            resource_name,
            resource_type,
            event_status,
            event_result,
            event,
        )
    else:
        logger.info(f"Event result is not monitorable: {event_result}")

    return {"messages": notification_messages}


if __name__ == "__main__":
    handler = logging.StreamHandler()
    logger.addHandler(handler)  # so we see logged messages in console when debugging    
    
    stage_name = "devam"
    
    from datetime import datetime, timezone, timedelta
    current_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    time_str = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    os.environ[
        "NOTIFICATION_QUEUE_URL"
    ] = f"https://sqs.eu-central-1.amazonaws.com/405389362913/queue-salmon-notification-{stage_name}"
    os.environ["SETTINGS_S3_PATH"] = f"s3://s3-salmon-settings-{stage_name}/settings/"
    os.environ[
        "ALERT_EVENTS_CLOUDWATCH_LOG_GROUP_NAME"
    ] = f"log-group-salmon-alert-events-{stage_name}"
    os.environ[
        "ALERT_EVENTS_CLOUDWATCH_LOG_STREAM_NAME"
    ] = f"log-stream-salmon-alert-events-{stage_name}"
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
        "time": time_str,
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
        "version": "4",
        "id": "315c1398-40ff-a850-213b-158f73e60175",
        "detail-type": "Step Functions Execution Status Change",
        "source": "aws.states",
        "account": "405389362913",
        "time": time_str,
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

    glue_workflow_event = {
        "version": "3",
        "id": "1c338584-7eb1-34e1-9f7d-f803fcb4ac22",
        "detail-type": "Glue Workflow State Change",
        "source": "salmon.glue_workflow",
        "account": "405389362913",
        "time": time_str,
        "region": "eu-central-1",
        "resources": [],
        "detail": {
            "workflowName": "glue-salmonts-workflow-dev",
            "state": "COMPLETED",
            "event_result": "FAILURE",
            "workflowRunId": "wr_75b9bcd0d7753776161d4ca1c4badd1924b445961ccdb89ae5ab86e920e6bc87",
            "message": "Test Workflow run execution status: failure",
            "origin_account": "025590872641",
            "origin_region": "eu-central-1"
        }
    }

    context = None
    response = lambda_handler(step_functions_event, context)
    print(response)
