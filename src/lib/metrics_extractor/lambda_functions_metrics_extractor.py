from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

import json

from lib.aws.cloudwatch_manager import CloudWatchManager
from lib.aws.lambda_manager import LambdaManager, LambdaInvocation
from lib.aws.events_manager import EventsManager
from lib.core.datetime_utils import datetime_to_epoch_milliseconds


class LambdaFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting lambda function metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[LambdaInvocation]:
        cloudwatch_man = CloudWatchManager(super().get_aws_service_client("logs"))
        lambda_man = LambdaManager(super().get_aws_service_client())
        lambda_invocations = lambda_man.get_lambda_invocations(
            cloudwatch_man, self.resource_name, since_time
        )
        return lambda_invocations

    def _data_to_timestream_records(
        self, lambda_invocations: list[LambdaInvocation]
    ) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []

        for lambda_invocation in lambda_invocations:
            if lambda_invocation.IsFinalState:
                dimensions = [
                    {
                        "Name": "lambda_function_request_id",
                        "Value": lambda_invocation.RequestId,
                    }
                ]

                # calculate GB_seconds metric
                GB_seconds = (lambda_invocation.MemorySize / 1024) * (
                    lambda_invocation.BilledDuration / 1000
                )
                metric_values = [
                    ("log_stream", lambda_invocation.LogStream, "VARCHAR"),
                    ("invocation", 1, "BIGINT"),
                    ("succeeded", int(lambda_invocation.IsSuccess), "BIGINT"),
                    ("failed", int(lambda_invocation.IsFailure), "BIGINT"),
                    ("status", lambda_invocation.Status, "VARCHAR"),
                    ("duration_ms", lambda_invocation.Duration, "DOUBLE"),
                    ("billed_duration_ms", lambda_invocation.BilledDuration, "DOUBLE"),
                    ("memory_size_mb", lambda_invocation.MemorySize, "DOUBLE"),
                    ("GB_seconds", GB_seconds, "DOUBLE"),
                    ("max_memory_used_mb", lambda_invocation.MaxMemoryUsed, "DOUBLE"),
                    ("error_message", lambda_invocation.ErrorString, "VARCHAR"),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = datetime_to_epoch_milliseconds(
                    lambda_invocation.StartedOn
                )

                records.append(
                    {
                        "Dimensions": dimensions,
                        "MeasureName": "invocation",
                        "MeasureValueType": "MULTI",
                        "MeasureValues": measure_values,
                        "Time": record_time,
                    }
                )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        self.lambda_invocations = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(
            self.lambda_invocations
        )
        return records, common_attributes

    ###########################################################################################
    def generate_event(
        self,
        lambdaInvocation: LambdaInvocation,
        event_bus_name: str,
        lambda_aws_account: str,  # region and account where lambda is deployed
        lambda_aws_region: str,
    ) -> dict:
        """
        Generates json in a form which can be sent to EventBus
        """

        event = {
            "Time": lambdaInvocation.CompletedOn,
            "Source": "salmon.lambda",
            "Resources": [],
            "DetailType": "Lambda Function Execution State Change",
            "Detail": json.dumps(
                {
                    "lambdaName": lambdaInvocation.LambdaName,
                    "state": lambdaInvocation.Status,
                    "message": lambdaInvocation.ErrorString,
                    "origin_account": lambda_aws_account,
                    "origin_region": lambda_aws_region,
                    "request_id": lambdaInvocation.RequestId,
                    "log_stream": lambdaInvocation.LogStream,
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
        if self.lambda_invocations:
            events = []
            for lambda_invocation in self.lambda_invocations:
                if lambda_invocation.IsFinalState:
                    events.append(
                        self.generate_event(
                            lambdaInvocation=lambda_invocation,
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
