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


def send_messages_to_sqs(queue_url: str, message_group_id: str, messages: list[dict]):
    """Sends messages array  to the given SQS queue

    Args:
        queue_url (str): SQS queue URL
        message_group_id (str): The tag that specifies that
            a message belongs to a specific message group
        messages (list[dict]): list of message objects
    """
    sender = SQSQueueSender(queue_url, message_group_id, sqs_client)
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
    mapper = EventMapperProvider.get_event_mapper(
        resource_type=resource_type, event=event, settings=settings
    )

    event_result = mapper.get_event_result()
    resource_name = mapper.get_resource_name()
    event_status = mapper.get_resource_state()
    execution_info_url = mapper.get_execution_info_url(resource_name)

    notification_messages = []

    event_is_alertable = event_result in EVENT_RESULTS_ALERTABLE
    if event_is_alertable:
        message = mapper.to_message()
        delivery_options = DeliveryOptionsResolver.get_delivery_options(
            settings, resource_name
        )

        notification_messages = map_to_notification_messages(message, delivery_options)

        logger.info(f"Notification messages: {notification_messages}")

        queue_url = os.environ["NOTIFICATION_QUEUE_URL"]
        send_messages_to_sqs(
            queue_url=queue_url,
            message_group_id=resource_name,
            messages=notification_messages,
        )

    else:
        logger.info(f"Event result is not alertable: {event_result}")

    event_is_monitorable = event_result in EVENT_RESULTS_MONITORABLE
    if event_is_monitorable:
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
            execution_info_url,
        )
    else:
        logger.info(f"Event result is not monitorable: {event_result}")

    return {
        "messages": notification_messages,
        "event_is_alertable": event_is_alertable,
        "event_is_monitorable": event_is_monitorable,
        "resource_type": resource_type,
        "execution_info_url": execution_info_url
    }
