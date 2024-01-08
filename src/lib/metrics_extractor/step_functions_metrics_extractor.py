from datetime import datetime

from lib.aws.step_functions_manager import StepFunctionsManager, ExecutionData
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
from lib.core import time_utils


class StepFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue job metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[ExecutionData]:
        step_functions_man = StepFunctionsManager(self.aws_service_client)
        step_function_executions = step_functions_man.get_step_function_executions(
            step_function_name=self.resource_name, since_time=since_time
        )
        return step_function_executions

    def _data_to_timestream_records(
        self, step_function_executions: list[ExecutionData]
    ) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for step_function_execution in step_function_executions:
            if StepFunctionsManager.is_final_state(
                step_function_execution.status
            ):  # exclude writing metrics for executions in progress
                dimensions = [
                    {
                        "Name": "step_function_run_id",
                        "Value": step_function_execution.name,
                    }
                ]

                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(step_function_execution.IsSuccess), "BIGINT"),
                    ("failed", int(step_function_execution.IsFailure), "BIGINT"),
                    ("duration_sec", step_function_execution.Duration, "DOUBLE"),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = time_utils.datetime_to_epoch_milliseconds(
                    step_function_execution.startDate
                )

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

    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):
        step_function_executions = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(
            step_function_executions
        )
        return records, common_attributes
