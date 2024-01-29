from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

from lib.aws.glue_manager import GlueManager, WorkflowRun
from lib.core import datetime_utils


class GlueWorkflowsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue job metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[WorkflowRun]:
        glue_man = GlueManager(super().get_aws_service_client())
        workflow_runs = glue_man.get_workflow_runs(
            workflow_name=self.resource_name, since_time=since_time
        )
        return workflow_runs

    def _data_to_timestream_records(self, workflow_runs: list[WorkflowRun]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for workflow_run in workflow_runs:
            if GlueManager.is_workflow_final_state(
                workflow_run.Status
            ):  # exclude writing metrics for Running/Waiting Job etc. (not finished)
                dimensions = [
                    {"Name": "workflow_run_id", "Value": workflow_run.WorkflowRunId}
                ]

                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(workflow_run.IsSuccess), "BIGINT"),
                    ("failed", int(workflow_run.IsFailure), "BIGINT"),
                    ("execution_time_sec", workflow_run.Duration, "DOUBLE"),
                    ("error_message", workflow_run.ErrorMessage, "VARCHAR"),
                    ("actions_total", workflow_run.Statistics.TotalActions, "BIGINT"),
                    (
                        "actions_timeouted",
                        workflow_run.Statistics.TimeoutActions,
                        "BIGINT",
                    ),
                    ("actions_failed", workflow_run.Statistics.FailedActions, "BIGINT"),
                    (
                        "actions_stopped",
                        workflow_run.Statistics.StoppedActions,
                        "BIGINT",
                    ),
                    (
                        "actions_succeeded",
                        workflow_run.Statistics.SucceededActions,
                        "BIGINT",
                    ),
                    (
                        "actions_errored",
                        workflow_run.Statistics.ErroredActions,
                        "BIGINT",
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

                record_time = datetime_utils.datetime_to_epoch_milliseconds(
                    workflow_run.StartedOn
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
        workflow_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(workflow_runs)
        return records, common_attributes
