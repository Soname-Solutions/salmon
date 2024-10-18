from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

import json

from lib.aws import (
    LambdaAttempt,
    LambdaManager,
    CloudWatchManager,
)
from lib.aws.lambda_manager import LambdaManager, LambdaAttempt
from lib.core.datetime_utils import datetime_to_epoch_milliseconds
from lib.aws.events_manager import EventsManager


class LambdaFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting lambda function metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[LambdaAttempt]:
        cloudwatch_man = CloudWatchManager(super().get_aws_service_client("logs"))
        lambda_man = LambdaManager(super().get_aws_service_client())
        lambda_attempts = lambda_man.get_lambda_attempts(
            cloudwatch_man, self.resource_name, since_time
        )
        return lambda_attempts

    def _data_to_timestream_records(self, lambda_attempts: list[LambdaAttempt]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []

        for lambda_attempt in lambda_attempts:
            if lambda_attempt.IsFinalState:
                dimensions = [
                    {
                        "Name": "lambda_function_request_id",
                        "Value": lambda_attempt.RequestId,
                    }
                ]

                # calculate GB_seconds metric
                GB_seconds = (lambda_attempt.MemorySize / 1024) * (
                    lambda_attempt.BilledDuration / 1000
                )
                metric_values = [
                    ("log_stream", lambda_attempt.LogStream, "VARCHAR"),
                    ("attempt", 1, "BIGINT"),
                    ("succeeded", int(lambda_attempt.IsSuccess), "BIGINT"),
                    ("failed", int(lambda_attempt.IsFailure), "BIGINT"),
                    ("status", lambda_attempt.Status, "VARCHAR"),
                    ("duration_ms", lambda_attempt.Duration, "DOUBLE"),
                    ("billed_duration_ms", lambda_attempt.BilledDuration, "DOUBLE"),
                    ("memory_size_mb", lambda_attempt.MemorySize, "DOUBLE"),
                    ("GB_seconds", GB_seconds, "DOUBLE"),
                    ("max_memory_used_mb", lambda_attempt.MaxMemoryUsed, "DOUBLE"),
                    ("error_message", lambda_attempt.ErrorString, "VARCHAR"),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = datetime_to_epoch_milliseconds(lambda_attempt.StartedOn)

                records.append(
                    {
                        "Dimensions": dimensions,
                        "MeasureName": "attempt",
                        "MeasureValueType": "MULTI",
                        "MeasureValues": measure_values,
                        "Time": record_time,
                    }
                )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        self.lambda_attempts = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(
            self.lambda_attempts
        )
        return records, common_attributes

    ###########################################################################################
    def generate_event(
        self,
        lambdaAttempt: LambdaAttempt,
        event_bus_name: str,
        lambda_aws_account: str,  # region and account where lambda is deployed
        lambda_aws_region: str,
    ) -> dict:
        """
        Generates json in a form which can be sent to EventBus
        """

        event = {
            "Time": lambdaAttempt.CompletedOn,
            "Source": "salmon.lambda",
            "Resources": [],
            "DetailType": "Lambda Function Execution State Change",
            "Detail": json.dumps(
                {
                    "lambdaName": lambdaAttempt.LambdaName,
                    "state": lambdaAttempt.Status,
                    "message": lambdaAttempt.ErrorString,
                    "origin_account": lambda_aws_account,
                    "origin_region": lambda_aws_region,
                    "request_id": lambdaAttempt.RequestId,
                    "log_stream": lambdaAttempt.LogStream,
                }
            ),
            "EventBusName": event_bus_name,
        }

        return event

    def send_alerts(
        self, event_bus_name: str, lambda_aws_account: str, lambda_aws_region: str
    ):
        """
        Sends events to EventBridge bus
        event_bus_name - target event_bus for the message
        lambda_aws_account, lambda_aws_region - where Lambda is deployed (so alerting service can recognize monitored_environment_name)
        """
        if self.lambda_attempts:
            events = []
            for lambda_attempt in self.lambda_attempts:
                if lambda_attempt.IsFinalState:
                    events.append(
                        self.generate_event(
                            lambdaAttempt=lambda_attempt,
                            event_bus_name=event_bus_name,
                            lambda_aws_account=lambda_aws_account,
                            lambda_aws_region=lambda_aws_region,
                        )
                    )

            if events:
                events_manager = EventsManager()
                event_count = len(events)
                print(f"Lambda extractor: Sending {event_count} events to EventBridge")
                events_manager.put_events(events=events)
                return {"events_sent": event_count}
