import logging
import json

from ..aws.cloudwatch_manager import CloudWatchEventsPublisher
from ..core import datetime_utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CloudWatchAlertWriter:
    @staticmethod
    def write_event_to_cloudwatch(
        log_group_name: str,
        log_stream_name: str,
        monitored_env_name: str,
        resource_name: str,
        resource_type: str,
        event_status: str,
        event_result: str,
        event: dict,
        execution_info_url: str,
    ):
        """
        Writes a given list of records to an Amazon CloudWatch logs.

        Uses an instance of CloudWatchEventPublisher to write the provided records to the
        specified CloudWatch log stream.

        Args:
            log_group_name (str): The name of the log group to put the event into.
            log_stream_name (str): The name of the log stream to put the event into.
            monitored_env_name (str): The name of the monitored environment.
            resource_name (str): The name of the AWS resource.
            resource_type (str): The type of the AWS resource.
            event_status (str): The status of the event.
            event_result (str): Result of the event.
            event (dict): The event dict to be written to the CloudWatch stream.
            execution_info_url (str): The link to the particular resource run.

        Returns:
            None: This function does not return anything but logs the outcome.
        """

        publisher = CloudWatchEventsPublisher(
            log_group_name=log_group_name,
            log_stream_name=log_stream_name,
        )

        logged_event = {}
        logged_event["event"] = event
        logged_event["monitored_environment"] = monitored_env_name
        logged_event["resource_name"] = resource_name
        logged_event["resource_type"] = resource_type
        logged_event["event_status"] = event_status
        logged_event["event_result"] = event_result
        logged_event["execution_info_url"] = execution_info_url

        logged_event_time = datetime_utils.iso_time_to_epoch_milliseconds(event["time"])
        result = publisher.put_event(
            logged_event_time, json.dumps(logged_event, indent=4)
        )

        logger.info("EventJSON has been written successfully")
        logger.info(result)
