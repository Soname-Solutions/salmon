from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

import json

from lib.aws import (
    LambdaExecution,
    LambdaManager,
    CloudWatchManager,
)
from lib.aws.lambda_manager import LambdaManager, LambdaExecution
from lib.core.datetime_utils import datetime_to_epoch_milliseconds
from lib.aws.events_manager import EventsManager


class LambdaFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting lambda function metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[LambdaExecution]:
        cloudwatch_man = CloudWatchManager(super().get_aws_service_client("logs"))
        lambda_man = LambdaManager(super().get_aws_service_client())
        lambda_runs = lambda_man.get_lambda_runs(
            cloudwatch_man, self.resource_name, since_time
        )
        return lambda_runs

    def _data_to_timestream_records(self, lambda_runs: list[LambdaExecution]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []

        for lambda_run in lambda_runs:
            if lambda_run.IsFinalState:
                dimensions = [
                    {
                        "Name": "lambda_function_request_id",
                        "Value": lambda_run.RequestId,
                    }
                ]

                # calculate GB_seconds metric
                GB_seconds = (lambda_run.MemorySize / 1024) * (
                    lambda_run.BilledDuration / 1000
                )
                metric_values = [
                    ("log_stream", lambda_run.LogStream, "VARCHAR"),
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(lambda_run.IsSuccess), "BIGINT"),
                    ("failed", int(lambda_run.IsFailure), "BIGINT"),
                    ("status", lambda_run.Status, "VARCHAR"),
                    ("duration_ms", lambda_run.Duration, "DOUBLE"),
                    ("billed_duration_ms", lambda_run.BilledDuration, "DOUBLE"),
                    ("memory_size_mb", lambda_run.MemorySize, "DOUBLE"),
                    ("GB_seconds", GB_seconds, "DOUBLE"),
                    ("max_memory_used_mb", lambda_run.MaxMemoryUsed, "DOUBLE"),
                    ("error_message", lambda_run.ErrorString, "VARCHAR"),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = datetime_to_epoch_milliseconds(lambda_run.StartedOn)

                records.append(
                    {
                        "Dimensions": dimensions,
                        "MeasureName": self.EXECUTION_MEASURE_NAME,
                        "MeasureValueType": "MULTI",
                        "MeasureValues": measure_values,
                        "Time": record_time,
                    }
                )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        self.lambda_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(self.lambda_runs)
        return records, common_attributes

    ###########################################################################################
    def generate_event(
        self,
        lambdaExecution: LambdaExecution,
        event_bus_name: str,
        lambda_aws_account: str,  # region and account where lambda is deployed
        lambda_aws_region: str,
    ) -> dict:
        """
        Generates json in a form which can be sent to EventBus
        """

        event = {
            "Time": lambdaExecution.CompletedOn,
            "Source": "salmon.lambda",
            "Resources": [],
            "DetailType": "Lambda Function Execution State Change",
            "Detail": json.dumps(
                {
                    "lambdaName": lambdaExecution.LambdaName,
                    "state": lambdaExecution.Status,
                    "message": lambdaExecution.ErrorString,
                    "origin_account": lambda_aws_account,
                    "origin_region": lambda_aws_region,
                    "request_id": lambdaExecution.RequestId,
                    "log_stream": lambdaExecution.LogStream,
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
        if self.lambda_runs:
            events = []
            for lambda_run in self.lambda_runs:
                events.append(
                    self.generate_event(
                        lambdaExecution=lambda_run,
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
