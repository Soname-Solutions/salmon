from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

import json

from lib.aws import (
    LogEntry,
    LambdaManager,
    CloudWatchManager,
    TimestreamTableWriter,
    TimeStreamQueryRunner,
)
from lib.core.constants import SettingConfigs
from lib.core.datetime_utils import datetime_to_epoch_milliseconds


class LambdaFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting lambda function metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[LogEntry]:
        cloudwatch_man = CloudWatchManager(super().get_aws_service_client("logs"))
        lambda_man = LambdaManager(super().get_aws_service_client())
        lambda_logs = lambda_man.get_lambda_logs(
            cloudwatch_man, self.resource_name, since_time
        )
        return lambda_logs

    def _data_to_timestream_records(self, lambda_logs: list[LogEntry]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []

        for lambda_log in lambda_logs:
            dimensions = [
                {
                    "Name": "lambda_function_request_id",
                    "Value": lambda_log.requestId if lambda_log.requestId else "n/a",
                }
            ]

            if lambda_log.IsReportEvent:
                GB_seconds = (
                    (lambda_log.MemorySize / 1024) * (lambda_log.BilledDuration / 1000)
                    if lambda_log.MemorySize and lambda_log.BilledDuration
                    else None
                )
                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("duration_ms", lambda_log.Duration, "DOUBLE"),
                    ("billed_duration_ms", lambda_log.BilledDuration, "DOUBLE"),
                    ("memory_size_mb", lambda_log.MemorySize, "DOUBLE"),
                    ("GB_seconds", GB_seconds, "DOUBLE"),
                    ("max_memory_used_mb", lambda_log.MaxMemoryUsed, "DOUBLE"),
                ]
            else:
                metric_values = [
                    (
                        "error_message",
                        lambda_log.message,
                        "VARCHAR",
                    ),
                ]

            measure_values = [
                {
                    "Name": metric_name,
                    "Value": str(metric_value),
                    "Type": metric_type,
                }
                for metric_name, metric_value, metric_type in metric_values
            ]

            record_time = datetime_to_epoch_milliseconds(lambda_log.timestamp)

            records.append(
                {
                    "Dimensions": dimensions,
                    "MeasureName": self.EXECUTION_MEASURE_NAME
                    if lambda_log.IsReportEvent
                    else self.ERROR_MEASURE_NAME,
                    "MeasureValueType": "MULTI",
                    "MeasureValues": measure_values,
                    "Time": record_time,
                }
            )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        lambda_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(lambda_runs)
        return records, common_attributes
