from datetime import datetime
from lib.aws.glue_manager import GlueManager, JobRun

from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
from lib.core import datetime_utils


class GlueJobsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue job metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[JobRun]:
        glue_man = GlueManager(super().get_aws_service_client())
        job_runs = glue_man.get_job_runs(
            job_name=self.resource_name, since_time=since_time
        )
        return job_runs

    def _data_to_timestream_records(self, job_runs: list[JobRun]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for job_run in job_runs:
            if GlueManager.is_job_final_state(
                job_run.JobRunState
            ):  # exclude writing metrics for Running/Waiting Job etc. (not finished)
                dimensions = [{"Name": "job_run_id", "Value": job_run.Id}]

                # Calculate DPU Seconds
                if job_run.DPUSeconds:
                    # if it's given by Glue explicitly (when auto-scaling is on))
                    dpu_seconds = job_run.DPUSeconds
                else:
                    # otherwise, we calculate - allocated capacity * execution time
                    # MaxCapacity is an up-to-date fields (instead of deprecated AllocatedCapacity)
                    dpu_seconds = float(job_run.ExecutionTime) * job_run.MaxCapacity

                dpu_seconds = round(dpu_seconds, 3)

                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(job_run.IsSuccess), "BIGINT"),
                    ("failed", int(job_run.IsFailure), "BIGINT"),
                    ("execution_time_sec", job_run.ExecutionTime, "DOUBLE"),
                    ("error_message", job_run.ErrorMessage, "VARCHAR"),
                    ("dpu_seconds", dpu_seconds, "DOUBLE"),
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
                    job_run.StartedOn
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

    def prepare_metrics_data(
        self, since_time: datetime, result_ids: list = []
    ) -> tuple[list, dict]:
        job_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(job_runs)
        return records, common_attributes
