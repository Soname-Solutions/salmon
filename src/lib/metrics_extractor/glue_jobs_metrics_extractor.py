from datetime import datetime
from lib.aws.glue_manager import GlueManager, JobRun
from lib.aws.timestream_manager import TimestreamTableWriter, TimeStreamQueryRunner
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor


class GlueJobsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue job metrics
    """ 

    def get_last_update_time(self, timestream_query_client) -> datetime:
        """
        Get time of this entity's data latest update (we append data since that time only)
        """
        queryRunner = TimeStreamQueryRunner(timestream_query_client=timestream_query_client)
        query = f'SELECT max(time) FROM "{self.timestream_db_name}"."{self.timestream_metrics_table_name}" WHERE job_name = \'{self.entity_name}\''
        last_date = queryRunner.execute_scalar_query_date_field(query=query)
        return last_date


    def _extract_metrics_data(self, since_time: datetime) -> list[JobRun]:
        glue_man = GlueManager(self.aws_service_client)
        job_runs = glue_man.get_job_runs(
            job_name=self.entity_name, since_time=since_time
        )
        return job_runs

    def _data_to_timestream_records(self, job_runs: list[JobRun]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": "job_name", "Value": self.entity_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for job_run in job_runs:
            if GlueManager.is_final_state(
                job_run.JobRunState
            ):  # exclude writing metrics for Running/Waiting Job etc. (not finished)
                dimensions = [{"Name": "job_run_id", "Value": job_run.Id}]

                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(job_run.IsSuccess), "BIGINT"),
                    ("failed", int(job_run.IsFailure), "BIGINT"),
                    ("execution_time_sec", job_run.ExecutionTime, "DOUBLE"),
                    ("error_message", job_run.ErrorMessage, "VARCHAR"),
                    ("dpu_seconds", job_run.DPUSeconds, "DOUBLE"),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = TimestreamTableWriter.datetime_to_epoch_milliseconds(
                    job_run.StartedOn
                )

                records.append(
                    {
                        "Dimensions": dimensions,
                        "MeasureName": "job_execution",
                        "MeasureValueType": "MULTI",
                        "MeasureValues": measure_values,
                        "Time": record_time,
                    }
                )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):
        job_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(job_runs)
        return records, common_attributes
      
        
