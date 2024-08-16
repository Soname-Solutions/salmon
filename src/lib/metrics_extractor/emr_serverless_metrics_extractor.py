from datetime import datetime

from lib.aws.emr_manager import EMRManager, EMRJobRunData
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
from lib.core import datetime_utils


class EMRServerlessMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting EMR Serverless metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[EMRJobRunData]:
        emr_man = EMRManager(super().get_aws_service_client())
        app_id = emr_man.get_application_id_by_name(app_name=self.resource_name)

        # list runs with finished state since a given time
        finished_states = emr_man.STATES_FAILURE + emr_man.STATES_SUCCESS
        runs_ids = emr_man.list_job_runs(
            app_id=app_id, since_time=since_time, states=finished_states
        )
        if not runs_ids:
            return []

        # extract detailed information about each finished run
        job_runs = [
            emr_man.get_job_run(app_id=app_id, run_id=run_id) for run_id in runs_ids
        ]
        return job_runs

    def _data_to_timestream_records(self, job_runs: list[EMRJobRunData]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for job_run in job_runs:
            dimensions = [{"Name": "job_run_id", "Value": job_run.jobRunId}]

            metric_values = [
                ("job_run_name", job_run.name, "VARCHAR"),
                ("app_id", job_run.applicationId, "VARCHAR"),
                ("execution", 1, "BIGINT"),
                ("succeeded", int(job_run.IsSuccess), "BIGINT"),
                ("failed", int(job_run.IsFailure), "BIGINT"),
                (
                    "execution_time_sec",
                    job_run.totalExecutionDurationSeconds,
                    "DOUBLE",
                ),
                ("error_message", job_run.ErrorMessage, "VARCHAR"),
                (
                    "total_vCPU_hour",
                    job_run.totalResourceUtilization.vCPUHour,
                    "DOUBLE",
                ),
                (
                    "total_memory_GB_hour",
                    job_run.totalResourceUtilization.memoryGBHour,
                    "DOUBLE",
                ),
                (
                    "total_storage_GB_hour",
                    job_run.totalResourceUtilization.storageGBHour,
                    "DOUBLE",
                ),
                (
                    "billed_vCPU_hour",
                    job_run.billedResourceUtilization.vCPUHour,
                    "DOUBLE",
                ),
                (
                    "billed_memory_GB_hour",
                    job_run.billedResourceUtilization.memoryGBHour,
                    "DOUBLE",
                ),
                (
                    "billed_storage_GB_hour",
                    job_run.billedResourceUtilization.storageGBHour,
                    "DOUBLE",
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
                job_run.createdAt
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

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        job_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(job_runs)
        return records, common_attributes
